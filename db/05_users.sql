CREATE TABLE IF NOT EXISTS app_user (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    salt          VARCHAR(64) NOT NULL,
    token         VARCHAR(255) UNIQUE,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_app_user_username ON app_user(username);
CREATE INDEX IF NOT EXISTS idx_app_user_token ON app_user(token);

CREATE TABLE IF NOT EXISTS user_favorite (
    user_id   INTEGER REFERENCES app_user(id) ON DELETE CASCADE,
    movie_id  INTEGER REFERENCES movie(id) ON DELETE CASCADE,
    added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, movie_id)
);

CREATE INDEX IF NOT EXISTS idx_user_favorite_user ON user_favorite(user_id);