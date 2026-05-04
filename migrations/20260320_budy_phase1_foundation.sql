-- Budy AI Phase 1 foundation
-- Introduces business units, sales catalog, public proposal publishing,
-- payment tracking, BCV rate snapshots, and service execution records.

BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'companies' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE public.companies
            ADD COLUMN organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_companies_organization_id ON public.companies (organization_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'requesters' AND column_name = 'organization_id'
    ) THEN
        ALTER TABLE public.requesters
            ADD COLUMN organization_id UUID REFERENCES public.organizations(id) ON DELETE SET NULL;
        CREATE INDEX IF NOT EXISTS idx_requesters_organization_id ON public.requesters (organization_id);
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.business_units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    slug TEXT NOT NULL,
    description TEXT,
    industry_context TEXT NOT NULL DEFAULT 'services',
    brand_name TEXT,
    brand_tagline TEXT,
    logo_url TEXT,
    primary_color TEXT,
    secondary_color TEXT,
    accent_color TEXT,
    support_email TEXT,
    support_phone TEXT,
    website_url TEXT,
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT business_units_org_slug_unique UNIQUE (organization_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_business_units_org_active
    ON public.business_units (organization_id, is_active);

CREATE TABLE IF NOT EXISTS public.catalog_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    business_unit_id UUID NOT NULL REFERENCES public.business_units(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT,
    unit TEXT NOT NULL DEFAULT 'servicio',
    pricing_model TEXT NOT NULL DEFAULT 'fixed_price',
    base_price_usd NUMERIC(12,2) NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_catalog_items_business_unit
    ON public.catalog_items (business_unit_id, is_active, category);

CREATE TABLE IF NOT EXISTS public.payment_methods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
    business_unit_id UUID NOT NULL REFERENCES public.business_units(id) ON DELETE CASCADE,
    method_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    account_holder TEXT,
    bank_name TEXT,
    phone TEXT,
    national_id TEXT,
    email TEXT,
    account_number TEXT,
    instructions TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT payment_methods_type_chk CHECK (
        method_type IN ('pago_movil', 'zelle', 'bank_transfer', 'cash_usd', 'pos', 'usdt')
    )
);

CREATE INDEX IF NOT EXISTS idx_payment_methods_business_unit
    ON public.payment_methods (business_unit_id, is_active, sort_order);

CREATE TABLE IF NOT EXISTS public.exchange_rate_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider TEXT NOT NULL,
    rate_type TEXT NOT NULL,
    base_currency TEXT NOT NULL DEFAULT 'USD',
    quote_currency TEXT NOT NULL DEFAULT 'VES',
    rate NUMERIC(18,6) NOT NULL,
    source_url TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    is_stale BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_exchange_rate_snapshots_lookup
    ON public.exchange_rate_snapshots (provider, rate_type, fetched_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'rfx_v2' AND column_name = 'business_unit_id'
    ) THEN
        ALTER TABLE public.rfx_v2
            ADD COLUMN business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL,
            ADD COLUMN industry_context TEXT,
            ADD COLUMN origin_channel TEXT NOT NULL DEFAULT 'document_upload',
            ADD COLUMN sales_stage TEXT NOT NULL DEFAULT 'draft',
            ADD COLUMN service_start_at TIMESTAMPTZ,
            ADD COLUMN service_end_at TIMESTAMPTZ,
            ADD COLUMN service_location TEXT,
            ADD COLUMN commercial_context JSONB NOT NULL DEFAULT '{}'::jsonb;
    END IF;
END $$;

ALTER TABLE public.rfx_v2
    DROP CONSTRAINT IF EXISTS rfx_v2_sales_stage_chk;

ALTER TABLE public.rfx_v2
    ADD CONSTRAINT rfx_v2_sales_stage_chk CHECK (
        sales_stage IN (
            'draft', 'sent', 'viewed', 'accepted', 'payment_pending',
            'partially_paid', 'confirmed', 'in_execution', 'completed', 'cancelled'
        )
    );

CREATE INDEX IF NOT EXISTS idx_rfx_v2_business_unit_stage
    ON public.rfx_v2 (business_unit_id, sales_stage, created_at DESC);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'generated_documents' AND column_name = 'public_token'
    ) THEN
        ALTER TABLE public.generated_documents
            ADD COLUMN business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL,
            ADD COLUMN public_token TEXT,
            ADD COLUMN public_visibility TEXT NOT NULL DEFAULT 'private',
            ADD COLUMN public_published_at TIMESTAMPTZ,
            ADD COLUMN public_expires_at TIMESTAMPTZ,
            ADD COLUMN public_view_count INTEGER NOT NULL DEFAULT 0,
            ADD COLUMN public_last_viewed_at TIMESTAMPTZ,
            ADD COLUMN pricing_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb;
    END IF;
END $$;

ALTER TABLE public.generated_documents
    DROP CONSTRAINT IF EXISTS generated_documents_public_visibility_chk;

ALTER TABLE public.generated_documents
    ADD CONSTRAINT generated_documents_public_visibility_chk CHECK (
        public_visibility IN ('private', 'public')
    );

CREATE UNIQUE INDEX IF NOT EXISTS idx_generated_documents_public_token_unique
    ON public.generated_documents (public_token)
    WHERE public_token IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_generated_documents_public_lookup
    ON public.generated_documents (public_visibility, public_published_at DESC);

CREATE TABLE IF NOT EXISTS public.proposal_acceptances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES public.generated_documents(id) ON DELETE CASCADE,
    rfx_id UUID NOT NULL REFERENCES public.rfx_v2(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL,
    accepted_name TEXT NOT NULL,
    accepted_email TEXT,
    accepted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_proposal_acceptances_proposal
    ON public.proposal_acceptances (proposal_id, accepted_at DESC);

CREATE TABLE IF NOT EXISTS public.payment_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proposal_id UUID NOT NULL REFERENCES public.generated_documents(id) ON DELETE CASCADE,
    rfx_id UUID NOT NULL REFERENCES public.rfx_v2(id) ON DELETE CASCADE,
    business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL,
    payment_method_id UUID REFERENCES public.payment_methods(id) ON DELETE SET NULL,
    acceptance_id UUID REFERENCES public.proposal_acceptances(id) ON DELETE SET NULL,
    payer_name TEXT,
    payer_email TEXT,
    payment_reference TEXT,
    amount_usd NUMERIC(12,2) NOT NULL DEFAULT 0,
    amount_ves NUMERIC(18,2),
    exchange_rate NUMERIC(18,6),
    proof_file_url TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'submitted',
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ,
    confirmed_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    CONSTRAINT payment_submissions_status_chk CHECK (status IN ('submitted', 'confirmed', 'rejected'))
);

CREATE INDEX IF NOT EXISTS idx_payment_submissions_proposal
    ON public.payment_submissions (proposal_id, submitted_at DESC);

CREATE TABLE IF NOT EXISTS public.service_orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rfx_id UUID NOT NULL REFERENCES public.rfx_v2(id) ON DELETE CASCADE,
    proposal_id UUID REFERENCES public.generated_documents(id) ON DELETE SET NULL,
    business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    service_start_at TIMESTAMPTZ,
    service_end_at TIMESTAMPTZ,
    service_location TEXT,
    notes TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by UUID REFERENCES public.users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT service_orders_status_chk CHECK (
        status IN ('draft', 'scheduled', 'in_execution', 'completed', 'cancelled')
    )
);

CREATE INDEX IF NOT EXISTS idx_service_orders_rfx
    ON public.service_orders (rfx_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $trigger$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$trigger$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_business_units_updated_at ON public.business_units;
CREATE TRIGGER update_business_units_updated_at
    BEFORE UPDATE ON public.business_units
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_catalog_items_updated_at ON public.catalog_items;
CREATE TRIGGER update_catalog_items_updated_at
    BEFORE UPDATE ON public.catalog_items
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_payment_methods_updated_at ON public.payment_methods;
CREATE TRIGGER update_payment_methods_updated_at
    BEFORE UPDATE ON public.payment_methods
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_service_orders_updated_at ON public.service_orders;
CREATE TRIGGER update_service_orders_updated_at
    BEFORE UPDATE ON public.service_orders
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

INSERT INTO public.business_units (
    organization_id,
    name,
    slug,
    description,
    industry_context,
    brand_name,
    is_default,
    is_active
)
SELECT
    o.id,
    o.name,
    COALESCE(NULLIF(o.slug, ''), regexp_replace(lower(o.name), '[^a-z0-9]+', '-', 'g')),
    'Default business unit created during Budy Phase 1 migration',
    'services',
    o.name,
    TRUE,
    TRUE
FROM public.organizations o
WHERE NOT EXISTS (
    SELECT 1
    FROM public.business_units bu
    WHERE bu.organization_id = o.id
);

UPDATE public.companies c
SET organization_id = u.organization_id
FROM public.users u
WHERE c.organization_id IS NULL
  AND c.user_id = u.id
  AND u.organization_id IS NOT NULL;

UPDATE public.requesters r
SET organization_id = c.organization_id
FROM public.companies c
WHERE r.organization_id IS NULL
  AND r.company_id = c.id
  AND c.organization_id IS NOT NULL;

UPDATE public.rfx_v2 r
SET
    business_unit_id = bu.id,
    industry_context = COALESCE(r.industry_context, NULLIF(r.rfx_type::text, ''), 'services'),
    sales_stage = COALESCE(
        r.sales_stage,
        CASE
            WHEN lower(COALESCE(r.status::text, '')) = 'completed' THEN 'completed'
            ELSE 'draft'
        END
    )
FROM public.business_units bu
WHERE bu.organization_id = r.organization_id
  AND bu.is_default = TRUE
  AND r.business_unit_id IS NULL;

UPDATE public.generated_documents gd
SET
    business_unit_id = COALESCE(gd.business_unit_id, r.business_unit_id),
    public_token = COALESCE(gd.public_token, encode(gen_random_bytes(18), 'hex')),
    public_visibility = COALESCE(gd.public_visibility, 'private'),
    pricing_snapshot = CASE
        WHEN gd.pricing_snapshot IS NULL OR gd.pricing_snapshot = '{}'::jsonb THEN
            jsonb_build_object(
                'contract_currency', 'USD',
                'reference_total_usd', COALESCE(gd.total_cost, 0),
                'backfilled_at', NOW()
            )
        ELSE gd.pricing_snapshot
    END
FROM public.rfx_v2 r
WHERE gd.rfx_id = r.id
  AND gd.document_type = 'proposal';

COMMIT;
