-- =========================
-- init.sql for Memory Search (Single-subject: Math)
-- Postgres + pgvector
-- =========================

-- 0) Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- 1) Enums
DO $$ BEGIN
  CREATE TYPE view_type AS ENUM ('problem', 'method', 'note', 'diagram', 'solution_outline');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

DO $$ BEGIN
  CREATE TYPE tag_tree_type AS ENUM ('topic', 'method', 'algebra_feature', 'geometry_feature');
EXCEPTION WHEN duplicate_object THEN null;
END $$;

-- =========================
-- 2) Core: Problem Items (source of truth)
-- =========================
CREATE TABLE IF NOT EXISTS problem_items (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- raw assets
  images           JSONB NOT NULL DEFAULT '[]'::jsonb,     -- ["path1","path2", ...]
  problem_text     TEXT  NOT NULL DEFAULT '',
  diagram_desc     TEXT  NOT NULL DEFAULT '',
  method_chain     TEXT  NOT NULL DEFAULT '',
  solution_outline TEXT  NOT NULL DEFAULT '',
  user_notes       TEXT  NOT NULL DEFAULT '',

  -- tags & meta
  user_tags        TEXT[] NOT NULL DEFAULT '{}'::text[],   -- quick manual tags
  meta             JSONB  NOT NULL DEFAULT '{}'::jsonb,    -- grade/source/chapter/difficulty/time...

  -- search baseline: one merged text for FTS
  bm25_text        TEXT NOT NULL DEFAULT '',

  -- full-text index column (generated)
  fts              TSVECTOR GENERATED ALWAYS AS (
                     to_tsvector('simple', coalesce(bm25_text,''))
                   ) STORED
);

CREATE INDEX IF NOT EXISTS idx_problem_items_fts       ON problem_items USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_problem_items_meta_gin  ON problem_items USING GIN (meta);
CREATE INDEX IF NOT EXISTS idx_problem_items_tags_gin  ON problem_items USING GIN (user_tags);

-- =========================
-- 3) Derived: Search Views (one item -> multiple searchable "documents")
-- =========================
CREATE TABLE IF NOT EXISTS search_views (
  id          BIGSERIAL PRIMARY KEY,
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  view_type   view_type NOT NULL,
  text        TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  fts         TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('simple', coalesce(text,''))
              ) STORED,

  UNIQUE(item_id, view_type)
);

CREATE INDEX IF NOT EXISTS idx_search_views_fts   ON search_views USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_search_views_item  ON search_views (item_id, view_type);

-- =========================
-- 4) Embeddings (per view_type)
-- NOTE: change vector dimension if you use a different embedding model
-- =========================
CREATE TABLE IF NOT EXISTS embeddings (
  id          BIGSERIAL PRIMARY KEY,
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  view_type   view_type NOT NULL,
  embedding   vector(1536) NOT NULL,   -- <-- change dimension if needed
  model       TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(item_id, view_type, model)
);

-- ANN index for cosine similarity
CREATE INDEX IF NOT EXISTS idx_embeddings_vec
  ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_embeddings_item ON embeddings (item_id, view_type);

-- =========================
-- 5) Feedback (thumb up/down)
-- =========================
CREATE TABLE IF NOT EXISTS feedback (
  id          BIGSERIAL PRIMARY KEY,
  query_id    UUID NOT NULL,
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  vote        SMALLINT NOT NULL CHECK (vote IN (1, -1)),
  reason      TEXT,
  ts          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_feedback_query ON feedback (query_id);
CREATE INDEX IF NOT EXISTS idx_feedback_item  ON feedback (item_id);

-- =========================
-- 6) Tag System (for hierarchical Tag-RAG / coarse-to-fine query planning)
-- =========================

-- 6.1 tag_nodes: store the taxonomy for math
-- tag_id uses TEXT so you can use stable readable IDs like:
-- "MATH/TOPIC/CONIC/TANGENT" or UUID strings, either works.
CREATE TABLE IF NOT EXISTS tag_nodes (
  tag_id         TEXT PRIMARY KEY,
  tree_type      tag_tree_type NOT NULL,

  name           TEXT NOT NULL,     -- e.g. "圆锥曲线"
  path           TEXT NOT NULL,     -- e.g. "数学/解析几何/圆锥曲线/切线与法线"
  level          INT  NOT NULL,     -- 1..N
  is_leaf        BOOLEAN NOT NULL DEFAULT false,

  parent_id      TEXT REFERENCES tag_nodes(tag_id) ON DELETE SET NULL,

  -- searchable text: path + synonyms + short description
  text_for_search TEXT NOT NULL DEFAULT '',
  fts            TSVECTOR GENERATED ALWAYS AS (
                   to_tsvector('simple', coalesce(text_for_search,''))
                 ) STORED,

  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tag_nodes_fts        ON tag_nodes USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_tag_nodes_tree_level ON tag_nodes (tree_type, level);
CREATE INDEX IF NOT EXISTS idx_tag_nodes_parent     ON tag_nodes (parent_id);

-- 6.2 item_leaf_tags: attach ONLY leaf tags to items (recommended)
-- This enables hard filtering before vector/FTS ranking.
CREATE TABLE IF NOT EXISTS item_leaf_tags (
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  tag_id      TEXT NOT NULL REFERENCES tag_nodes(tag_id) ON DELETE CASCADE,
  tree_type   tag_tree_type NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  PRIMARY KEY (item_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_item_leaf_tags_tag  ON item_leaf_tags (tag_id);
CREATE INDEX IF NOT EXISTS idx_item_leaf_tags_item ON item_leaf_tags (item_id);

-- =========================
-- (Optional) 7) Search logging tables (helpful for eval & replay)
-- Uncomment if you want query logs from day 1.
-- =========================
-- CREATE TABLE IF NOT EXISTS search_queries (
--   id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
--   created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
--   raw_query    TEXT NOT NULL,
--   queryplan    JSONB,
--   meta_filters JSONB,
--   top_k        INT NOT NULL DEFAULT 30
-- );
--
-- CREATE TABLE IF NOT EXISTS search_query_results (
--   id        BIGSERIAL PRIMARY KEY,
--   query_id  UUID NOT NULL REFERENCES search_queries(id) ON DELETE CASCADE,
--   item_id   UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
--   scores    JSONB NOT NULL,
--   evidence  JSONB,
--   rank      INT NOT NULL,
--   UNIQUE(query_id, item_id)
-- );

-- End of init.sql

