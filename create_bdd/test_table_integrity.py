import psycopg2

# --- INITIALISATION ---
print("🔌 Connexion à la base de données 'movies'...")
try:
    conn = psycopg2.connect(dbname="movies", user="jiwonie", host="localhost", password="")
    cursor = conn.cursor()
except Exception as e:
    print(f"❌ Erreur de connexion : {e}")
    exit()

# ==========================================
# TEST 1 : COMPTAGE DE TOUTES LES TABLES
# ==========================================
def verifier_comptage_tables():
    print("\n📊 --- 1. VÉRIFICATION DU REMPLISSAGE DES TABLES ---")
    
    tables_principales = ['movie', 'human', 'keyword', 'genre', 'tag', 'company', 'country', 'language']
    tables_liaisons = ['movie_human', 'movie_keyword', 'movie_genre', 'movie_tag', 'movie_company', 'movie_country', 'movie_language']
    
    print("\n📦 TABLES PRINCIPALES (Entités) :")
    for table in tables_principales:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            compte = cursor.fetchone()[0]
            icone = "✅" if compte > 0 else "❌"
            print(f"  {icone} {table.ljust(15)} : {compte} lignes")
        except Exception as e:
            print(f"  ⚠️ Erreur sur {table} : {e}")
            conn.rollback()

    print("\n🔗 TABLES DE LIAISON (Relations) :")
    for table in tables_liaisons:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            compte = cursor.fetchone()[0]
            icone = "✅" if compte > 0 else "❌"
            print(f"  {icone} {table.ljust(15)} : {compte} liaisons")
        except Exception as e:
            print(f"  ⚠️ Erreur sur {table} : {e}")
            conn.rollback()


# ==========================================
# TEST 2 : LE RAYON X D'UN FILM (Test des JOIN)
# ==========================================
def faire_rayon_x_film():
    print("\n🔎 --- 2. TEST D'INTÉGRITÉ RELATIONNELLE (Le Rayon X) ---")
    
    # On prend un film très populaire au hasard pour avoir un maximum de données
    cursor.execute("""
        SELECT id, title, popularity 
        FROM movie 
        WHERE popularity > 20 AND overview IS NOT NULL 
        ORDER BY RANDOM() 
        LIMIT 1;
    """)
    film = cursor.fetchone()
    
    if not film:
        print("❌ Impossible de trouver un film pour le test.")
        return
        
    movie_id, title, popularity = film
    print(f"\n🎬 Film sélectionné : {title} (ID: {movie_id})")
    
    # 1. Test des Genres
    cursor.execute("""
        SELECT g.genre FROM genre g 
        JOIN movie_genre mg ON g.id = mg.genre_id 
        WHERE mg.movie_id = %s;
    """, (movie_id,))
    genres = [row[0] for row in cursor.fetchall()]
    print(f"   🎭 Genres     : {', '.join(genres) if genres else 'Aucun'}")
    
    # 2. Test des Tags
    cursor.execute("""
        SELECT t.name FROM tag t 
        JOIN movie_tag mt ON t.id = mt.tag_id 
        WHERE mt.movie_id = %s;
    """, (movie_id,))
    tags = [row[0] for row in cursor.fetchall()]
    print(f"   🏷️  Tags       : {', '.join(tags) if tags else 'Aucun'}")
    
    # 3. Test des Mots-clés (limité à 5 pour l'affichage)
    cursor.execute("""
        SELECT k.word FROM keyword k 
        JOIN movie_keyword mk ON k.id = mk.keyword_id 
        WHERE mk.movie_id = %s LIMIT 5;
    """, (movie_id,))
    keywords = [row[0] for row in cursor.fetchall()]
    print(f"   🔑 Mots-clés  : {', '.join(keywords) if keywords else 'Aucun'}")

    # 4. Test du Réalisateur
    cursor.execute("""
        SELECT h.name_human FROM human h 
        JOIN movie_human mh ON h.id = mh.human_id 
        WHERE mh.movie_id = %s AND mh.role_human = 'Director';
    """, (movie_id,))
    realisateurs = [row[0] for row in cursor.fetchall()]
    print(f"   🎬 Réalisateur: {', '.join(realisateurs) if realisateurs else 'Inconnu'}")
    
    # 5. Test des Acteurs (limité à 3)
    cursor.execute("""
        SELECT h.name_human, mh.character_name FROM human h 
        JOIN movie_human mh ON h.id = mh.human_id 
        WHERE mh.movie_id = %s AND mh.role_human = 'Actor' LIMIT 3;
    """, (movie_id,))
    acteurs = cursor.fetchall()
    if acteurs:
        print("   👥 Acteurs    :")
        for acteur, personnage in acteurs:
            print(f"      - {acteur} (dans le rôle de : {personnage})")
    else:
        print("   👥 Acteurs    : Aucun")

    # 6. Test des Compagnies de Production
    cursor.execute("""
        SELECT c.name_company FROM company c 
        JOIN movie_company mc ON c.id = mc.company_id 
        WHERE mc.movie_id = %s LIMIT 3;
    """, (movie_id,))
    compagnies = [row[0] for row in cursor.fetchall()]
    print(f"   🏢 Production : {', '.join(compagnies) if compagnies else 'Aucune'}")


# ==========================================
# EXÉCUTION
# ==========================================
verifier_comptage_tables()
faire_rayon_x_film()

cursor.close()
conn.close()
print("\n✅ Test terminé.")