import psycopg2
from pgvector.psycopg2 import register_vector

# --- INITIALISATION ---
# Remarque : Pas de "SentenceTransformer" ici ! Le script est ultra-léger et rapide.
print("🔌 Connexion à la base de données...")
conn = psycopg2.connect(dbname="movies", user="jiwonie", host="localhost", password="")
cursor = conn.cursor()
register_vector(conn)

# ==========================================
# MOTEUR DE RECOMMANDATION (FILMS SIMILAIRES)
# ==========================================
def trouver_films_similaires(titre_cible, top_final=5):
    print(f"\n" + "═"*70)
    print(f"🍿 FILMS SIMILAIRES À : '{titre_cible}'")
    print("═"*70)

    # ---------------------------------------------------------
    # ÉTAPE 1 : Récupérer "l'ADN" (les 3 vecteurs) du film cible
    # ---------------------------------------------------------
    # On utilise ILIKE avec des % pour pardonner les petites erreurs de titre
    cursor.execute("""
        SELECT id, title, embedding_synopsis, embedding_keyword, embedding_tag
        FROM movie 
        WHERE title ILIKE %s AND embedding_synopsis IS NOT NULL 
        LIMIT 1;
    """, (f"%{titre_cible}%",))
    
    film_ref = cursor.fetchone()
    
    if not film_ref:
        print(f"❌ Impossible de trouver '{titre_cible}' (ou il n'a pas été vectorisé).")
        return
        
    ref_id, vrai_titre, emb_syn, emb_key, emb_tag = film_ref
    print(f"✅ Film de référence trouvé : {vrai_titre}\n")

    # Sécurité technique : Si un film n'a pas de tag ou de mot-clé, 
    # on envoie un vecteur bidon presque à zéro pour éviter que la DB ne plante
    vecteur_vide = [0.0001] * 384
    emb_key = emb_key if emb_key is not None else vecteur_vide
    emb_tag = emb_tag if emb_tag is not None else vecteur_vide

    # ---------------------------------------------------------
    # ÉTAPE 2 : La formule Ultime (Sémantique pure avec Poids Dynamiques)
    # ---------------------------------------------------------
    requete_similaires = """
        WITH calculs AS (
            SELECT title,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie 
            -- Très important : on exclut le film lui-même des résultats !
            WHERE embedding_synopsis IS NOT NULL AND id != %s
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn, 
                   GREATEST(MAX(s_key), 0.001) AS m_key, 
                   GREATEST(MAX(s_tag), 0.001) AS m_tag 
            FROM calculs
        )
        SELECT c.title,
               -- Ta fameuse formule proportionnelle
               (c.s_syn * (m.m_syn / (m.m_syn + m.m_key + m.m_tag)) + 
                c.s_key * (m.m_key / (m.m_syn + m.m_key + m.m_tag)) + 
                c.s_tag * (m.m_tag / (m.m_syn + m.m_key + m.m_tag))) AS score_final
        FROM calculs c CROSS JOIN maxima m
        ORDER BY score_final DESC 
        LIMIT %s;
    """
    
    # On envoie les vecteurs du film cible pour comparer avec tout le reste
    cursor.execute(requete_similaires, (emb_syn, emb_key, emb_tag, ref_id, top_final))
    resultats = cursor.fetchall()
    
    for i, (titre, s_final) in enumerate(resultats, 1):
        print(f"  {i}. {titre} (Similitude: {s_final*100:.1f}%)")


# ==========================================
# EXÉCUTION DES TESTS
# ==========================================

# Testons avec des styles très différents !
trouver_films_similaires("The Dark Knight Rises", top_final=5)
trouver_films_similaires("Toy Story", top_final=5)
trouver_films_similaires("Interstellar", top_final=5)

cursor.close()
conn.close()