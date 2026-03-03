-- ========================================
-- MIGRATION 012: Pre-RFX processing sessions
-- ========================================
-- Objetivo:
-- - Permitir flujo extracción -> chat de revisión -> confirmación -> persistencia final
-- - Evitar creación de rfx_v2 antes de confirmación del usuario

CREATE TABLE IF NOT EXISTS public.rfx_processing_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    organization_id UUID NULL,
    status TEXT NOT NULL DEFAULT 'clarification',
    review_required BOOLEAN NOT NULL DEFAULT TRUE,
    review_confirmed BOOLEAN NOT NULL DEFAULT FALSE,
    confirmed_rfx_id UUID NULL,
    preview_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    validated_data JSONB NOT NULL DEFAULT '{}'::jsonb,
    evaluation_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    conversation_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    recent_events JSONB NOT NULL DEFAULT '[]'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '24 hours'),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT rfx_processing_sessions_status_chk
      CHECK (status IN ('active', 'clarification', 'ready_for_confirm', 'confirmed', 'expired'))
);

CREATE INDEX IF NOT EXISTS idx_rfx_processing_sessions_user ON public.rfx_processing_sessions (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rfx_processing_sessions_org ON public.rfx_processing_sessions (organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_rfx_processing_sessions_status ON public.rfx_processing_sessions (status);
CREATE INDEX IF NOT EXISTS idx_rfx_processing_sessions_expires_at ON public.rfx_processing_sessions (expires_at);

CREATE OR REPLACE FUNCTION public.touch_rfx_processing_sessions_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_touch_rfx_processing_sessions_updated_at ON public.rfx_processing_sessions;
CREATE TRIGGER trg_touch_rfx_processing_sessions_updated_at
BEFORE UPDATE ON public.rfx_processing_sessions
FOR EACH ROW
EXECUTE FUNCTION public.touch_rfx_processing_sessions_updated_at();

COMMENT ON TABLE public.rfx_processing_sessions IS 'Sesiones temporales pre-RFX para revisión conversacional antes de persistir rfx_v2';
