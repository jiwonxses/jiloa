import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# --- 1. INITIALISATION ---
print("Chargement du modèle...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

conn = psycopg2.connect(dbname="movies", user="jiwonie", host="localhost", password="")
cursor = conn.cursor()
register_vector(conn)

# ==========================================
# TEST 1 : VÉRIFICATION DES DONNÉES
# ==========================================
def tester_statistiques():
    print("\n--- 1. STATISTIQUES DE LA BASE ---")
    
    cursor.execute("SELECT COUNT(*) FROM movie;")
    nb_films = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM movie WHERE embedding_synopsis IS NOT NULL;")
    nb_vecteurs = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM human;")
    nb_humains = cursor.fetchone()[0]
    
    print(f"🎬 Films importés : {nb_films}")
    print(f"🧠 Films vectorisés : {nb_vecteurs}")
    print(f"👤 Acteurs/Techniciens : {nb_humains}")


# ==========================================
# TEST 2 : RECHERCHE TEXTUELLE (FAUTES DE FRAPPE)
# ==========================================
def tester_recherche_titre(recherche_titre):
    print(f"\n--- 2. RECHERCHE LEXICALE (GIN) : '{recherche_titre}' ---")
    
    requete_sql = """
        SELECT title, similarity(title, %s) AS score_typo
        FROM movie
        -- On double le symbole pour cent pour que psycopg2 ne le confonde pas avec une variable
        WHERE title %% %s 
        ORDER BY score_typo DESC
        LIMIT 5;
    """
    
    cursor.execute(requete_sql, (recherche_titre, recherche_titre))
    resultats = cursor.fetchall()
    
    if not resultats:
        print("Aucun titre similaire trouvé.")
    else:
        for titre, score in resultats:
            print(f"- {titre} (Correspondance : {score*100:.1f}%)")


# ==========================================
# TEST 3 : RECHERCHE SÉMANTIQUE HYBRIDE
# ==========================================
def tester_recherche_semantique(phrase, top_final=5):
    print(f"\n--- 3. RECHERCHE VECTORIELLE : '{phrase}' ---")
    
    # On génère le vecteur de la recherche
    embedding_requete = model.encode(phrase).tolist()
    
    requete_sql = """
        -- ETAPE 1 : On calcule les 3 scores de similarité pour chaque film
        WITH calculs_bruts AS (
            SELECT title, popularity,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie
            WHERE embedding_synopsis IS NOT NULL
        ),
        
        -- ETAPE 2 : On trouve le MEILLEUR score absolu de la base pour chaque catégorie
        maxima AS (
            SELECT
                -- On met 0.001 au minimum pour empêcher une division par zéro plus tard
                GREATEST(MAX(s_syn), 0.001) AS max_syn,
                GREATEST(MAX(s_key), 0.001) AS max_key,
                GREATEST(MAX(s_tag), 0.001) AS max_tag
            FROM calculs_bruts
        ),
        
        -- ETAPE 3 : On applique ta formule mathématique !
        scores_ponderes AS (
            SELECT c.title, c.popularity, c.s_syn, c.s_key, c.s_tag,
                   
                   -- Tes coefficients dynamiques
                   (m.max_syn / (m.max_syn + m.max_key + m.max_tag)) AS coef_syn,
                   (m.max_key / (m.max_syn + m.max_key + m.max_tag)) AS coef_key,
                   (m.max_tag / (m.max_syn + m.max_key + m.max_tag)) AS coef_tag,
                   
                   -- La note sémantique hybride
                   (
                       c.s_syn * (m.max_syn / (m.max_syn + m.max_key + m.max_tag)) +
                       c.s_key * (m.max_key / (m.max_syn + m.max_key + m.max_tag)) +
                       c.s_tag * (m.max_tag / (m.max_syn + m.max_key + m.max_tag))
                   ) AS score_semantique
                   
            FROM calculs_bruts c CROSS JOIN maxima m
        )
        
        -- ETAPE 4 : Calcul final avec le bonus de popularité (Multiplicateur MAX +50 pourcent)
        SELECT title, popularity, score_semantique, s_syn, s_key, s_tag, coef_syn, coef_key, coef_tag,
               -- On multiplie le score de base par (1 + jusqu'à 0.5 de bonus)
               score_semantique * (1.0 + 0.5 * LEAST(COALESCE(popularity, 0) / 100.0, 1.0)) AS score_final
        FROM scores_ponderes
        -- Le filtre indispensable pour que les films hors-sujet ne profitent pas du +50 pourcent
        WHERE score_semantique > 0.25 
        ORDER BY score_final DESC
        LIMIT %s;
    """
    
    # On passe le vecteur 3 fois (Syn, Key, Tag) et la limite de résultats
    cursor.execute(requete_sql, (embedding_requete, embedding_requete, embedding_requete, top_final))
    resultats = cursor.fetchall()
    
    # Affichage intelligent
    if resultats:
        # On récupère les coefficients de la première ligne (ils sont les mêmes pour tous les films sur cette recherche)
        c_syn, c_key, c_tag = resultats[0][6], resultats[0][7], resultats[0][8]
        print(f"📊 Poids dynamiques calculés pour cette requête : Synopsis {c_syn*100:.1f}% | Mots-clés {c_key*100:.1f}% | Tags {c_tag*100:.1f}%\n")
        
        for i, (titre, pop, s_sim, s_syn, s_key, s_tag, _, _, _, s_final) in enumerate(resultats, 1):
            print(f"{i}. {titre} (Popularité: {pop})")
            print(f"   Score final: {s_final*100:.1f}% | (Sémantique pur: {s_sim*100:.1f}%)")
            print(f"   Détail IA  -> Syn: {s_syn*100:.0f}% | Key: {s_key*100:.0f}% | Tag: {s_tag*100:.0f}%")
    else:
        print("Aucun film suffisamment pertinent trouvé pour cette recherche.")


# ==========================================
# EXÉCUTION DES TESTS
# ==========================================

# 1. Vérifie si l'importation a bien marché
tester_statistiques()

# 2. Teste le pardon des fautes de frappe (ex: "Avatarr" au lieu de "Avatar")
tester_recherche_titre("Wall-E")
tester_recherche_titre("Imception")

# 3. Teste la compréhension de l'IA et le pont avec les genres
tester_recherche_semantique("Mafieux italien, famille")
tester_recherche_semantique("Un robot sur terre qui s'occupe des déchet")

cursor.close()
conn.close()