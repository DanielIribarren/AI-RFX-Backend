-- Corporate document codes for RFX and proposals
-- Date: 2026-02-25

-- 1) RFX code stored directly on rfx_v2
ALTER TABLE IF EXISTS rfx_v2
  ADD COLUMN IF NOT EXISTS rfx_code TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_rfx_v2_rfx_code_unique
  ON rfx_v2 (rfx_code)
  WHERE rfx_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_rfx_v2_rfx_code_pattern
  ON rfx_v2 (rfx_code text_pattern_ops);

-- 2) Proposal code fields on generated_documents
ALTER TABLE IF EXISTS generated_documents
  ADD COLUMN IF NOT EXISTS proposal_code TEXT,
  ADD COLUMN IF NOT EXISTS rfx_code_snapshot TEXT,
  ADD COLUMN IF NOT EXISTS proposal_revision INTEGER;

CREATE UNIQUE INDEX IF NOT EXISTS idx_generated_documents_proposal_code_unique
  ON generated_documents (proposal_code)
  WHERE proposal_code IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_documents_proposal_code_pattern
  ON generated_documents (proposal_code text_pattern_ops);

CREATE INDEX IF NOT EXISTS idx_generated_documents_rfx_code_snapshot
  ON generated_documents (rfx_code_snapshot);

CREATE INDEX IF NOT EXISTS idx_generated_documents_rfx_id_created_at
  ON generated_documents (rfx_id, created_at DESC);

-- 3) Global sequence table by code type + domain + year
CREATE TABLE IF NOT EXISTS document_code_sequences (
  code_type TEXT NOT NULL CHECK (code_type IN ('rfx', 'proposal')),
  domain_prefix TEXT NOT NULL,
  year INTEGER NOT NULL,
  last_value INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (code_type, domain_prefix, year)
);

-- 4) Per-RFX proposal revision sequence
CREATE TABLE IF NOT EXISTS proposal_code_revisions (
  rfx_id UUID PRIMARY KEY,
  last_revision INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 5) Atomic function: next sequence for code_type/domain/year
CREATE OR REPLACE FUNCTION next_document_code_seq(
  p_code_type TEXT,
  p_domain_prefix TEXT,
  p_year INTEGER
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_next INTEGER;
BEGIN
  IF p_code_type NOT IN ('rfx', 'proposal') THEN
    RAISE EXCEPTION 'Invalid code type: %', p_code_type;
  END IF;

  IF p_domain_prefix IS NULL OR length(trim(p_domain_prefix)) = 0 THEN
    RAISE EXCEPTION 'Domain prefix cannot be empty';
  END IF;

  INSERT INTO document_code_sequences (code_type, domain_prefix, year, last_value)
  VALUES (lower(trim(p_code_type)), upper(trim(p_domain_prefix)), p_year, 1)
  ON CONFLICT (code_type, domain_prefix, year)
  DO UPDATE SET
    last_value = document_code_sequences.last_value + 1,
    updated_at = NOW()
  RETURNING last_value INTO v_next;

  RETURN v_next;
END;
$$;

-- 6) Atomic function: next proposal revision per RFX
CREATE OR REPLACE FUNCTION next_proposal_revision(
  p_rfx_id UUID
)
RETURNS INTEGER
LANGUAGE plpgsql
AS $$
DECLARE
  v_next INTEGER;
BEGIN
  IF p_rfx_id IS NULL THEN
    RAISE EXCEPTION 'RFX id cannot be null';
  END IF;

  INSERT INTO proposal_code_revisions (rfx_id, last_revision)
  VALUES (p_rfx_id, 1)
  ON CONFLICT (rfx_id)
  DO UPDATE SET
    last_revision = proposal_code_revisions.last_revision + 1,
    updated_at = NOW()
  RETURNING last_revision INTO v_next;

  RETURN v_next;
END;
$$;
