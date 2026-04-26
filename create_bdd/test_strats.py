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
# FONCTION AUXILIAIRE : EXÉCUTE LES 3 BIAIS
# ==========================================
def executer_variantes(nom_niveau, base_cte, emb_params, top_final):
    print(f"\n" + "─"*60)
    print(f" 🧩 NIVEAU : {nom_niveau} ")
    print("─"*60)

    # 1. SANS BIAIS (Sémantique Pure)
    req_pure = base_cte + f"""
        SELECT title, score_semantique AS score_final 
        FROM scores ORDER BY score_final DESC LIMIT {top_final};
    """
    cursor.execute(req_pure, emb_params)
    print("  🔹 SANS BIAIS (Sémantique pure) :")
    for i, (titre, score) in enumerate(cursor.fetchall(), 1):
        print(f"     {i}. {titre} ({score*100:.1f}%)")

    # 2. BIAIS POPULARITÉ (+50% MAX)
    req_pop = base_cte + f"""
        SELECT title, score_semantique * (1.0 + 0.5 * LEAST(COALESCE(popularity, 0) / 100.0, 1.0)) AS score_final 
        FROM scores WHERE score_semantique > 0.25 ORDER BY score_final DESC LIMIT {top_final};
    """
    cursor.execute(req_pop, emb_params)
    resultats_pop = cursor.fetchall()
    print("\n  🌟 AVEC POPULARITÉ (+50% max) :")
    if resultats_pop:
        for i, (titre, score) in enumerate(resultats_pop, 1):
            print(f"     {i}. {titre} ({score*100:.1f}%)")
    else:
        print("     ⚠️ Aucun film n'a passé le filtre anti-poubelle (> 25%).")

    # 3. BIAIS NOTE CRITIQUE (+50% MAX)
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


# ==========================================
# LA MATRICE DE RECHERCHE GLOBALE
# ==========================================
def comparer_matrice(phrase, top_final=3):
    print(f"\n" + "═"*70)
    print(f"🎯 RECHERCHE : '{phrase}'")
    print("═"*70)
    
    # On génère l'embedding UNE seule fois, c'est ce qui rend le script ultra rapide !
    emb = model.encode(phrase).tolist()

    # ---------------------------------------------------------
    # NIVEAU 1 : SYNOPSIS UNIQUEMENT
    # ---------------------------------------------------------
    cte_1 = """
        WITH scores AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS score_semantique
            FROM movie WHERE embedding_synopsis IS NOT NULL
        )
    """
    executer_variantes("100% SYNOPSIS", cte_1, (emb,), top_final)

    # ---------------------------------------------------------
    # NIVEAU 2 : SYNOPSIS + TAGS (Poids Dynamique)
    # ---------------------------------------------------------
    cte_2 = """
        WITH calculs AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie WHERE embedding_synopsis IS NOT NULL
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn, 
                   GREATEST(MAX(s_tag), 0.001) AS m_tag 
            FROM calculs
        ),
        scores AS (
            SELECT c.title, c.popularity, c.vote_average, c.vote_count,
                   (c.s_syn * (m.m_syn / (m.m_syn + m.m_tag)) + 
                    c.s_tag * (m.m_tag / (m.m_syn + m.m_tag))) AS score_semantique
            FROM calculs c CROSS JOIN maxima m
        )
    """
    executer_variantes("SYNOPSIS + TAGS", cte_2, (emb, emb), top_final)

    # ---------------------------------------------------------
    # NIVEAU 3 : LA TOTALE (Syn + Key + Tag avec Poids Dynamique)
    # ---------------------------------------------------------
    cte_3 = """
        WITH calculs AS (
            SELECT title, popularity, vote_average, vote_count,
                   (1 - (embedding_synopsis <=> %s::vector)) AS s_syn,
                   COALESCE((1 - (embedding_keyword <=> %s::vector)), 0) AS s_key,
                   COALESCE((1 - (embedding_tag <=> %s::vector)), 0) AS s_tag
            FROM movie WHERE embedding_synopsis IS NOT NULL
        ),
        maxima AS (
            SELECT GREATEST(MAX(s_syn), 0.001) AS m_syn, 
                   GREATEST(MAX(s_key), 0.001) AS m_key, 
                   GREATEST(MAX(s_tag), 0.001) AS m_tag 
            FROM calculs
        ),
        scores AS (
            SELECT c.title, c.popularity, c.vote_average, c.vote_count,
                   (c.s_syn * (m.m_syn / (m.m_syn + m.m_key + m.m_tag)) + 
                    c.s_key * (m.m_key / (m.m_syn + m.m_key + m.m_tag)) + 
                    c.s_tag * (m.m_tag / (m.m_syn + m.m_key + m.m_tag))) AS score_semantique
            FROM calculs c CROSS JOIN maxima m
        )
    """
    executer_variantes("LA TOTALE (Synopsis + Keywords + Tags)", cte_3, (emb, emb, emb), top_final)


# ==========================================
# EXÉCUTION DU BANC D'ESSAI
# ==========================================

# Tu vas voir instantanément comment chaque couche (Mots-clés, Tags, Popularité, Notes) 
# modifie le classement de ces 3 recherches :
comparer_matrice("Des dinosaures sur une ile qui agresse les héros", top_final=3)
comparer_matrice("Un robot qui nettoie la planète Terre", top_final=3)
comparer_matrice("Un film avec des superhéros qui sauvent l'univers", top_final=3)

cursor.close()
conn.close()