import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# --- INITIALISATION ---
print("Chargement du modèle...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

conn = psycopg2.connect(dbname="movies", user="jiwonie", host="localhost", password="")
cursor = conn.cursor()
register_vector(conn)

# ==========================================
# 1. PREUVE DE L'EXISTENCE
# ==========================================
def enquete_jurassic_park():
    print("\n" + "═"*70)
    print("🔎 RECHERCHE DE 'JURASSIC PARK' DANS LA BDD")
    print("═"*70)
    
    # On cherche tout ce qui contient "Jurassic" dans le titre
    cursor.execute("""
        SELECT id, title, popularity, vote_average, 
               (embedding_synopsis IS NOT NULL) as est_vectorise
        FROM movie 
        WHERE title ILIKE '%jurassic%' OR title ILIKE '%jurassic%'
        ORDER BY popularity DESC;
    """)
    
    resultats = cursor.fetchall()
    
    if not resultats:
        print("❌ AUCUN FILM contenant 'Jurassic' n'a été trouvé ! Le problème vient de l'importation.")
        return False
    
    print("✅ Films trouvés :")
    for id_film, titre, pop, note, vect in resultats:
        statut = "🧠 Vectorisé" if vect else "⚠️ Non Vectorisé (Pas de synopsis ?)"
        print(f"  - {titre} (ID: {id_film}) | Pop: {pop} | Note: {note} | Statut: {statut}")
    return True


# ==========================================
# FONCTIONS DE LA MATRICE (Tes 9 tests)
# ==========================================
def executer_variantes(nom_niveau, base_cte, emb_params, top_final):
    print(f"\n" + "─"*60)
    print(f" 🧩 NIVEAU : {nom_niveau} ")
    print("─"*60)

    req_pure = base_cte + f"""
        SELECT title, score_semantique AS score_final 
        FROM scores ORDER BY score_final DESC LIMIT {top_final};
    """
    cursor.execute(req_pure, emb_params)
    print("  🔹 SANS BIAIS (Sémantique pure) :")
    for i, (titre, score) in enumerate(cursor.fetchall(), 1):
        print(f"     {i}. {titre} ({score*100:.1f}%)")

    # 2. BIAIS POPULARITÉ (+50% MAX NON LINÉAIRE)
    req_pop = base_cte + f"""
        SELECT title, 
               score_semantique * (1.0 + 0.5 * (COALESCE(popularity, 0) / (COALESCE(popularity, 0) + 15.0))) AS score_final 
        FROM scores 
        WHERE score_semantique > 0.25 
        ORDER BY score_final DESC LIMIT {top_final};
    """
    cursor.execute(req_pop, emb_params)
    resultats_pop = cursor.fetchall()
    print("\n  🌟 AVEC POPULARITÉ (+50% max) :")
    if resultats_pop:
        for i, (titre, score) in enumerate(resultats_pop, 1):
            print(f"     {i}. {titre} ({score*100:.1f}%)")
    else:
        print("     ⚠️ Aucun film n'a passé le filtre anti-poubelle (> 25%).")

    req_note = base_cte + f"""
        SELECT title, score_semantique * (1.0 + 0.5 * (COALESCE(vote_average, 0) / 10.0) * LEAST(COALESCE(vote_count, 1) / 50.0, 1.0)) AS score_final 
        FROM scores WHERE score_semantique > 0.25 ORDER BY score_final DESC LIMIT {top_final};
    """
    cursor.execute(req_note, emb_params)
    resultats_note = cursor.fetchall()
    print("\n  ⭐ AVEC NOTES (+50% max) :")
    if resultats_note:
        for i, (titre, score) in enumerate(resultats_note, 1):
            print(f"     {i}. {titre} ({score*100:.1f}%)")
    else:
        print("     ⚠️ Aucun film n'a passé le filtre anti-poubelle (> 25%).")


def comparer_matrice(phrase, top_final=5): # On passe à 5 pour creuser un peu !
    print(f"\n" + "═"*70)
    print(f"🎯 RECHERCHE : '{phrase}'")
    print("═"*70)
    
    emb = model.encode(phrase).tolist()

    cte_1 = """
        WITH scores AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS score_semantique
            FROM movie WHERE embedding_synopsis IS NOT NULL
        )
    """
    executer_variantes("100% SYNOPSIS", cte_1, (emb,), top_final)

    cte_2 = """
        WITH calculs AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie WHERE embedding_synopsis IS NOT NULL
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn, GREATEST(MAX(s_tag), 0.001) AS m_tag FROM calculs
        ),
        scores AS (
            SELECT c.title, c.popularity, c.vote_average, c.vote_count,
                   (c.s_syn * (m.m_syn / (m.m_syn + m.m_tag)) + c.s_tag * (m.m_tag / (m.m_syn + m.m_tag))) AS score_semantique
            FROM calculs c CROSS JOIN maxima m
        )
    """
    executer_variantes("SYNOPSIS + TAGS", cte_2, (emb, emb), top_final)

    cte_3 = """
        WITH calculs AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie WHERE embedding_synopsis IS NOT NULL
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn, GREATEST(MAX(s_key), 0.001) AS m_key, GREATEST(MAX(s_tag), 0.001) AS m_tag FROM calculs
        ),
        scores AS (
            SELECT c.title, c.popularity, c.vote_average, c.vote_count,
                   (
                        (c.s_syn * 3.0 * (m.m_syn / (m.m_syn + m.m_key + m.m_tag))) + 
                        (c.s_key * 1.0 * (m.m_key / (m.m_syn + m.m_key + m.m_tag))) + 
                        (c.s_tag * 2.0 * (m.m_tag / (m.m_syn + m.m_key + m.m_tag)))
                    ) / ( (3.0 * m.m_syn + m.m_key + 2.0 * m.m_tag) / (m.m_syn + m.m_key + m.m_tag) ) AS score_semantique
            FROM calculs c CROSS JOIN maxima m
        )
    """
    executer_variantes("LA TOTALE (Synopsis + Keywords + Tags)", cte_3, (emb, emb, emb), top_final)


# ==========================================
# EXÉCUTION
# ==========================================

if enquete_jurassic_park():
    comparer_matrice("Un parc d'attractions avec des dinosaures créés par ADN", top_final=5)

cursor.close()
conn.close()