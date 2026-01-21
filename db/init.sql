-- =========================
-- init.sql for Memory Search (Single-subject: Math)
-- Postgres + pgvector + SCWS(zhparser)
-- =========================

-- 0) Extensions
-- 必须先加载 pgvector 和 pgcrypto
CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS vector;

-- [新增] 0.1) 加载中文分词扩展 zhparser (SCWS 的 Postgres 包装器)
CREATE EXTENSION IF NOT EXISTS zhparser;

-- [新增] 0.2) 定义中文全文检索配置 zhcfg
-- 如果配置不存在才创建 (防止报错)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'zhcfg') THEN
        CREATE TEXT SEARCH CONFIGURATION zhcfg (PARSER = zhparser);
        -- 将名词(n), 动词(v), 形容词(a), 成语(i), 叹词(e), 习用语(l) 映射为 simple 类型
        ALTER TEXT SEARCH CONFIGURATION zhcfg ADD MAPPING FOR n,v,a,i,e,l WITH simple;
    END IF;
END
$$;

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
  images           JSONB NOT NULL DEFAULT '[]'::jsonb,
  problem_text     TEXT  NOT NULL DEFAULT '',
  diagram_desc     TEXT  NOT NULL DEFAULT '',
  method_chain     TEXT  NOT NULL DEFAULT '',
  solution_outline TEXT  NOT NULL DEFAULT '',
  user_notes       TEXT  NOT NULL DEFAULT '',

  -- tags & meta
  user_tags        TEXT[] NOT NULL DEFAULT '{}'::text[],
  meta             JSONB  NOT NULL DEFAULT '{}'::jsonb,

  -- search baseline: one merged text for FTS
  bm25_text        TEXT NOT NULL DEFAULT '',

  -- full-text index column (generated)
  -- 这里的 'zhcfg' 现在已经定义好了，不会报错
  fts              TSVECTOR GENERATED ALWAYS AS (
                     to_tsvector('zhcfg', coalesce(bm25_text,''))
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

  -- [修复] 修正了这里的拼写错误 'zh c f g' -> 'zhcfg'
  fts         TSVECTOR GENERATED ALWAYS AS (
                to_tsvector('zhcfg', coalesce(text,''))
              ) STORED,

  UNIQUE(item_id, view_type)
);

CREATE INDEX IF NOT EXISTS idx_search_views_fts   ON search_views USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_search_views_item  ON search_views (item_id, view_type);

-- =========================
-- 4) Embeddings (per view_type)
-- =========================
CREATE TABLE IF NOT EXISTS embeddings (
  id          BIGSERIAL PRIMARY KEY,
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  view_type   view_type NOT NULL,
  embedding   vector(1536) NOT NULL,
  model       TEXT NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE(item_id, view_type, model)
);

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
-- 6) Tag System
-- =========================
CREATE TABLE IF NOT EXISTS tag_nodes (
  tag_id         TEXT PRIMARY KEY,
  tree_type      tag_tree_type NOT NULL,

  name           TEXT NOT NULL,
  path           TEXT NOT NULL,
  level          INT  NOT NULL,
  is_leaf        BOOLEAN NOT NULL DEFAULT false,

  parent_id      TEXT REFERENCES tag_nodes(tag_id) ON DELETE SET NULL,

  -- searchable text
  text_for_search TEXT NOT NULL DEFAULT '',
  -- 这里也使用了 zhcfg
  fts            TSVECTOR GENERATED ALWAYS AS (
                   to_tsvector('zhcfg', coalesce(text_for_search,''))
                 ) STORED,

  created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tag_nodes_fts        ON tag_nodes USING GIN (fts);
CREATE INDEX IF NOT EXISTS idx_tag_nodes_tree_level ON tag_nodes (tree_type, level);
CREATE INDEX IF NOT EXISTS idx_tag_nodes_parent     ON tag_nodes (parent_id);

-- 6.2 item_leaf_tags
CREATE TABLE IF NOT EXISTS item_leaf_tags (
  item_id     UUID NOT NULL REFERENCES problem_items(id) ON DELETE CASCADE,
  tag_id      TEXT NOT NULL REFERENCES tag_nodes(tag_id) ON DELETE CASCADE,
  tree_type   tag_tree_type NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),

  PRIMARY KEY (item_id, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_item_leaf_tags_tag  ON item_leaf_tags (tag_id);
CREATE INDEX IF NOT EXISTS idx_item_leaf_tags_item ON item_leaf_tags (item_id);
