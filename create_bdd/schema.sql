-- 1. Nettoyage : On supprime tout en cascade pour éviter les erreurs si les tables existent déjà
DROP TABLE IF EXISTS movie_country CASCADE;
DROP TABLE IF EXISTS movie_language CASCADE;
DROP TABLE IF EXISTS movie_keyword CASCADE;
DROP TABLE IF EXISTS movie_human CASCADE;
DROP TABLE IF EXISTS movie_company CASCADE;
DROP TABLE IF EXISTS movie_genre CASCADE;
DROP TABLE IF EXISTS movie_tag CASCADE;

DROP TABLE IF EXISTS rating CASCADE;
DROP TABLE IF EXISTS human CASCADE;
DROP TABLE IF EXISTS keyword CASCADE;
DROP TABLE IF EXISTS country CASCADE;
DROP TABLE IF EXISTS language CASCADE;
DROP TABLE IF EXISTS company CASCADE;
DROP TABLE IF EXISTS genre CASCADE;
DROP TABLE IF EXISTS movie CASCADE;
DROP TABLE IF EXISTS tag CASCADE;

-- ==========================================
-- 2. TABLES PRINCIPALES (Les Entités)
-- ==========================================

CREATE TABLE movie (
    id INTEGER PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    date_publication DATE,
    poster TEXT,
    adult BOOLEAN DEFAULT FALSE,
    overview TEXT,
    popularity NUMERIC,
    tmdb_id INTEGER,
    vote_average NUMERIC,
    vote_count INTEGER
);

CREATE TABLE language (
    id VARCHAR(10) PRIMARY KEY,
    name_language VARCHAR(100) NOT NULL
);

CREATE TABLE country (
    id VARCHAR(10) PRIMARY KEY,
    name_country VARCHAR(100) NOT NULL
);

CREATE TABLE keyword (
    id INTEGER PRIMARY KEY,
    word VARCHAR(100) NOT NULL
);

-- J'ai retiré "role" d'ici, car une même personne peut être Acteur dans un film et Réalisateur dans un autre !
CREATE TABLE human (
    id INTEGER PRIMARY KEY,
    name_human VARCHAR(255) NOT NULL
);

-- Si une note est spécifique à un film, on la relie directement à l'ID du film
CREATE TABLE rating (
    id INTEGER PRIMARY KEY,
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    note NUMERIC -- Permet de stocker des notes comme 8.5
);

CREATE TABLE company (
    id INTEGER PRIMARY KEY,
    name_company VARCHAR(255) NOT NULL
);

CREATE TABLE genre (
    id INTEGER PRIMARY KEY,
    genre VARCHAR(255) NOT NULL
);

CREATE TABLE tag (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL 
);

-- ==========================================
-- 3. TABLES DE LIAISON (Les relations Many-to-Many)
-- ==========================================

-- Relie les films et les pays
CREATE TABLE movie_country (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    country_id VARCHAR(10) REFERENCES country(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, country_id) -- Empêche d'ajouter deux fois le même pays au même film
);

-- Relie les films et les langues (avec une option pour savoir si c'est la langue originale)
CREATE TABLE movie_language (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    language_id VARCHAR(10) REFERENCES language(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, language_id)
);

-- Relie les films et les mots-clés
CREATE TABLE movie_keyword (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    keyword_id INTEGER REFERENCES keyword(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, keyword_id)
);

-- La table la plus complète : relie le Film, l'Humain, son Rôle exact, et le Personnage qu'il joue (en texte)
CREATE TABLE movie_human (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    human_id INTEGER REFERENCES human(id) ON DELETE CASCADE,
    character_name TEXT, -- L'information vient se ranger directement ici !
    role_human VARCHAR(100) NOT NULL, -- Ex: 'Director', 'Actor', 'Producer'
    PRIMARY KEY (movie_id, human_id, role_human)
);

CREATE TABLE movie_company (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    company_id INTEGER REFERENCES company(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, company_id)
);

CREATE TABLE movie_genre (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    genre_id INTEGER REFERENCES genre(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

CREATE TABLE movie_tag (
    movie_id INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    tag_id INTEGER REFERENCES tag(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, tag_id)
);