import json
import csv
import psycopg2
import ast
from psycopg2.extras import execute_batch
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

# ==========================================
# PHASE 1 : CONNEXION ET STRUCTURE DE LA BDD
# ==========================================
print("--- PHASE 1 : Préparation de la base de données ---")
conn = psycopg2.connect(dbname="movies", user="jiwonie", host="localhost", password="")
conn.autocommit = True 
cursor = conn.cursor()

print("Création des tables classiques...")
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/schema.sql', 'r', encoding='utf-8') as file:
    schema = file.read()
cursor.execute(schema)

print("Configuration des extensions (pg_trgm et vector)...")
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

# Création des 3 colonnes vectorielles !
cursor.execute("ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_synopsis VECTOR(384);")
cursor.execute("ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_keyword VECTOR(384);")
cursor.execute("ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_tag VECTOR(384);")
register_vector(conn)

print("Création des index (GIN pour le texte, HNSW pour les vecteurs)...")
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_movie_title_trgm ON movie USING GIN (title gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_human_name_trgm ON human USING GIN (name_human gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_character_name_trgm ON movie_human USING GIN (character_name gin_trgm_ops);
    CREATE INDEX IF NOT EXISTS idx_movie_synopsis_hnsw ON movie USING hnsw (embedding_synopsis vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_movie_keyword_hnsw ON movie USING hnsw (embedding_keyword vector_cosine_ops);
    CREATE INDEX IF NOT EXISTS idx_movie_tag_hnsw ON movie USING hnsw (embedding_tag vector_cosine_ops);
""")

# ==========================================
# PHASE 2 : IMPORTATION DES DONNÉES (CSV)
# ==========================================
print("\n--- PHASE 2 : Importation des données CSV ---")

print("Importation des films (movies_metadata.csv)...")
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/movies_metadata.csv', 'r', encoding='utf-8') as fichier:
    lecteur_csv = csv.DictReader(fichier)
    for ligne in lecteur_csv:
        try:
            movie_id = ligne.get('id')
            if not movie_id or not str(movie_id).isdigit():
                continue

            titre_final = ligne.get('title')
            if not titre_final:
                titre_final = ligne.get('original_title')
            if not titre_final:
                titre_final = "Titre inconnu"

            cursor.execute("""
                INSERT INTO movie (id, title, date_publication, poster, adult, overview, popularity, vote_average, vote_count) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING;
            """, (
                ligne['id'], titre_final,
                ligne['release_date'] if ligne.get('release_date') else None,
                ligne.get('poster_path'), ligne.get('adult', False), ligne.get('overview'),
                ligne['popularity'] if ligne.get('popularity') else None,
                ligne['vote_average'] if ligne.get('vote_average') else None,
                ligne['vote_count'] if ligne.get('vote_count') else 0
            ))

            if ligne.get('genres'):
                for genre in ast.literal_eval(ligne['genres']):
                    cursor.execute("INSERT INTO genre (id, genre) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (genre['id'], genre['name']))
                    cursor.execute("INSERT INTO movie_genre (movie_id, genre_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (movie_id, genre['id']))
            if ligne.get('production_countries'):
                for p in ast.literal_eval(ligne['production_countries']):
                    cursor.execute("INSERT INTO country (id, name_country) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (p['iso_3166_1'], p['name']))
                    cursor.execute("INSERT INTO movie_country (movie_id, country_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (movie_id, p['iso_3166_1']))
            if ligne.get('spoken_languages'):
                for l in ast.literal_eval(ligne['spoken_languages']):
                    cursor.execute("INSERT INTO language (id, name_language) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (l['iso_639_1'], l['name']))
                    cursor.execute("INSERT INTO movie_language (movie_id, language_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (movie_id, l['iso_639_1']))
            if ligne.get('production_companies'):
                for c in ast.literal_eval(ligne['production_companies']):
                    cursor.execute("INSERT INTO company (id, name_company) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (c['id'], c['name']))
                    cursor.execute("INSERT INTO movie_company (movie_id, company_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (movie_id, c['id']))
        except Exception as e:
            pass

# --- LA MAGIE DES TAGS COMMENCE ICI ---
print("Création du dictionnaire de traduction (links.csv)...")
ml_to_tmdb = {}
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/link.csv', 'r', encoding='utf-8') as fichier:
    for ligne in csv.DictReader(fichier):
        try:
            if ligne['tmdbId'] and ligne['movieId']:
                cursor.execute("UPDATE movie SET tmdb_id = %s WHERE id = %s;", (ligne['tmdbId'], ligne['tmdbId']))
                ml_to_tmdb[ligne['movieId']] = ligne['tmdbId']
        except Exception:
            pass

print("Importation des TAGS UTILISATEURS (tags.csv)...")
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/tag.csv', 'r', encoding='utf-8') as fichier:
    lecteur_csv = csv.DictReader(fichier)
    tags_existants = set()
    for ligne in lecteur_csv:
        try:
            ml_id = ligne.get('movieId')
            tag_name = ligne.get('tag')
            
            # Si le tag existe et qu'on a la traduction du film
            if tag_name and ml_id in ml_to_tmdb:
                tmdb_id = ml_to_tmdb[ml_id]
                tag_name_clean = tag_name.strip().lower() # On nettoie la donnée
                
                tag_id = abs(hash(tag_name_clean)) % (10 ** 8) 
                
                if tag_name_clean not in tags_existants:
                    cursor.execute("INSERT INTO tag (id, name) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (tag_id, tag_name_clean))
                    tags_existants.add(tag_name_clean)
                
                cursor.execute("INSERT INTO movie_tag (movie_id, tag_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (tmdb_id, tag_id))
        except Exception:
            pass
# --------------------------------------

print("Importation des mots-clés (keywords.csv)...")
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/keywords.csv', 'r', encoding='utf-8') as fichier:
    for ligne in csv.DictReader(fichier):
        try:
            if ligne['keywords']:
                for kw in ast.literal_eval(ligne['keywords']):
                    cursor.execute("INSERT INTO keyword (id, word) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (kw['id'], kw['name']))
                    cursor.execute("INSERT INTO movie_keyword (movie_id, keyword_id) VALUES (%s, %s) ON CONFLICT DO NOTHING;", (ligne['id'], kw['id']))
        except Exception:
            pass

print("Importation de l'équipe (credits.csv)...")
jobs_importants = ['Director', 'Producer', 'Screenplay', 'Novel', 'Original Music Composer', 'Director of Photography']
with open('/Users/jiwonie/Desktop/jiloa/PROJECT/create_bdd/credits.csv', 'r', encoding='utf-8') as fichier:
    for ligne in csv.DictReader(fichier):
        try:
            if ligne['cast']:
                for c in ast.literal_eval(ligne['cast']):
                    if c['order'] <= 15:
                        cursor.execute("INSERT INTO human (id, name_human) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (c['id'], c['name']))
                        cursor.execute("INSERT INTO movie_human (movie_id, human_id, role_human, character_name) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;", (ligne['id'], c['id'], 'Actor', c['character']))
            if ligne['crew']:
                for c in ast.literal_eval(ligne['crew']):
                    if c['job'] in jobs_importants:
                        cursor.execute("INSERT INTO human (id, name_human) VALUES (%s, %s) ON CONFLICT (id) DO NOTHING;", (c['id'], c['name']))
                        cursor.execute("INSERT INTO movie_human (movie_id, human_id, role_human, character_name) VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING;", (ligne['id'], c['id'], c['job'], None))
        except Exception:
            pass

print("Importation des données textuelles terminée avec succès !")

# ==========================================
# PHASE 3 : RÉCUPÉRATION POUR VECTORISATION
# ==========================================
print("\n--- PHASE 3 : Préparation pour la vectorisation ---")
print("Chargement du modèle d'embedding (MiniLM)...")
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2') 

# On récupère tout (y compris les fameux tags !)
cursor.execute("""
    SELECT 
        m.id, 
        m.overview, 
        (
            SELECT STRING_AGG(k.word, ', ') 
            FROM movie_keyword mk JOIN keyword k ON mk.keyword_id = k.id WHERE mk.movie_id = m.id
        ) AS keywords,
        (
            SELECT STRING_AGG(g.genre, ', ') 
            FROM movie_genre mg JOIN genre g ON mg.genre_id = g.id WHERE mg.movie_id = m.id
        ) AS genres,
        (
            SELECT STRING_AGG(t.name, ', ') 
            FROM movie_tag mt JOIN tag t ON mt.tag_id = t.id WHERE mt.movie_id = m.id
        ) AS tags
    FROM movie m
    WHERE m.embedding_synopsis IS NULL AND m.overview IS NOT NULL;
""")

films_a_traiter = cursor.fetchall()
print(f"{len(films_a_traiter)} films à vectoriser trouvés.")

# ==========================================
# PHASE 4 : GÉNÉRATION DES EMBEDDINGS (3 Vecteurs)
# ==========================================
if films_a_traiter:
    print("\n--- PHASE 4 : Génération et enregistrement des vecteurs ---")
    conn.autocommit = False 
    
    taille_lot = 500
    requete_update = "UPDATE movie SET embedding_synopsis = %s, embedding_keyword = %s, embedding_tag = %s WHERE id = %s"

    for i in range(0, len(films_a_traiter), taille_lot):
        lot = films_a_traiter[i:i+taille_lot]
        
        synopsis_list = []
        metadata_list = [] 
        tag_list = []
        ids_films = []
        
        for film_id, overview, keywords, genres, tags in lot:
            synopsis_list.append(overview)
            
            texte_genres = f"Genres : {genres}" if genres else ""
            texte_keywords = f"Mots-clés : {keywords}" if keywords else ""
            texte_metadata = f"{texte_genres} | {texte_keywords}".strip(" |")
            
            texte_tag = f"Tags : {tags}" if tags else ""

            metadata_list.append(texte_metadata)
            tag_list.append(texte_tag)
            ids_films.append(film_id)
        
        print(f"Génération en cours pour les films {i+1} à {min(i+len(lot), len(films_a_traiter))}...")
        
        embeddings_synopsis = model.encode(synopsis_list)
        embeddings_metadata = model.encode(metadata_list)
        embeddings_tags = model.encode(tag_list)
        
        donnees_maj = [
            (
                emb_syn.tolist(), 
                emb_meta.tolist() if metadata_list[idx] else None, 
                emb_tag.tolist() if tag_list[idx] else None, 
                ids_films[idx]
            ) 
            for idx, (emb_syn, emb_meta, emb_tag) in enumerate(zip(embeddings_synopsis, embeddings_metadata, embeddings_tags))
        ]
        
        execute_batch(cursor, requete_update, donnees_maj)
        conn.commit()

print("\n🚀 Terminé ! La base de données est construite, remplie et vectorisée avec succès !")
cursor.close()
conn.close()