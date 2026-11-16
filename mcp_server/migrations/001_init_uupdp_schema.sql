-- 1. Mengaktifkan ekstensi pgvector jika belum aktif
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Membuat tabel pelacak versi migrasi
CREATE TABLE IF NOT EXISTS schema_migrations (
    version VARCHAR(50) PRIMARY KEY,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Membuat tabel dokumen naskah Undang-Undang Perlindungan Data Pribadi (UU No. 27 Tahun 2022)
CREATE TABLE IF NOT EXISTS uupdp_dokumen (
    id SERIAL PRIMARY KEY,
    judul VARCHAR(255) NOT NULL,
    bab VARCHAR(255),
    pasal VARCHAR(100),
    kategori VARCHAR(50) DEFAULT 'Batang Tubuh',
    konten TEXT NOT NULL,
    embedding VECTOR(768) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Indeks HNSW untuk pencarian vektor cepat (Cosine Distance)
CREATE INDEX IF NOT EXISTS idx_uupdp_embedding_hnsw
ON uupdp_dokumen USING hnsw (embedding vector_cosine_ops);

-- 5. Indeks B-Tree & GIN untuk filter pasal, bab, kategori, dan metadata
CREATE INDEX IF NOT EXISTS idx_uupdp_pasal ON uupdp_dokumen (pasal);
CREATE INDEX IF NOT EXISTS idx_uupdp_bab ON uupdp_dokumen (bab);
CREATE INDEX IF NOT EXISTS idx_uupdp_kategori ON uupdp_dokumen (kategori);
CREATE INDEX IF NOT EXISTS idx_uupdp_metadata ON uupdp_dokumen USING gin (metadata);

-- 6. Indeks GIN untuk Weighted Full-Text Search (Leksikal)
CREATE INDEX IF NOT EXISTS idx_uupdp_fts
ON uupdp_dokumen USING gin (
    (setweight(to_tsvector('simple', coalesce(judul, '') || ' ' || coalesce(bab, '')), 'A') ||
     setweight(to_tsvector('simple', coalesce(konten, '')), 'D'))
);
