ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_synopsis VECTOR(384);
ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_keyword VECTOR(384);
ALTER TABLE movie ADD COLUMN IF NOT EXISTS embedding_tag VECTOR(384);

-- Table de tracking pour l'idempotence du seeder
CREATE TABLE IF NOT EXISTS db_init_status (
    step VARCHAR(50) PRIMARY KEY,
    completed_at TIMESTAMP DEFAULT NOW()
);