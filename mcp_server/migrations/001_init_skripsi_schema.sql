-- 1. Mengaktifkan ekstensi vektor untuk embeddings
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Membuat tabel pelacak versi migrasi
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Membuat tabel dokumen naskah skripsi
CREATE TABLE IF NOT EXISTS skripsi_dokumen (
    id SERIAL PRIMARY KEY,
    judul VARCHAR(255) NOT NULL,
    konten TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Membuat indeks HNSW untuk pencarian vektor cepat (Cosine Distance)
CREATE INDEX IF NOT EXISTS idx_skripsi_embedding_hnsw 
ON skripsi_dokumen USING hnsw (embedding vector_cosine_ops);