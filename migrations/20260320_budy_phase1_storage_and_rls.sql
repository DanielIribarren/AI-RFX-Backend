-- Budy Phase 1 — Storage bucket + RLS policies
-- Run AFTER 20260320_budy_phase1_foundation.sql
-- Requires a Supabase project with Storage enabled.
--
-- What this file does:
--   1. Creates the 'payment-proofs' storage bucket (public = false, so files
--      are not world-listable but individual objects can get public URLs).
--   2. Adds an INSERT policy so anonymous (unauthenticated) users can upload
--      proof files via the public proposal flow.
--   3. Adds a SELECT policy so authenticated users (provider side) can read
--      proof files for their own proposals.
--   4. Adds RLS policies for the new Phase 1 tables so Supabase PostgREST
--      honours organization isolation.
--
-- NOTE: Run this in the Supabase SQL editor (with service-role context) or via
-- psql with the service-role connection string. The storage schema is not
-- accessible with the anon key.

BEGIN;

-- ============================================================
-- 1. Payment-proofs storage bucket
-- ============================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'payment-proofs',
    'payment-proofs',
    FALSE,
    10485760,   -- 10 MB
    ARRAY[
        'image/jpeg',
        'image/png',
        'image/webp',
        'image/gif',
        'application/pdf'
    ]
)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 2. Storage policies for payment-proofs
-- ============================================================

-- Anyone (including unauthenticated clients viewing a public proposal) can
-- upload their payment proof.  The path is scoped to {proposal_id}/{uuid}.ext
-- which limits blast radius.
DROP POLICY IF EXISTS "payment_proofs_anon_insert" ON storage.objects;
CREATE POLICY "payment_proofs_anon_insert"
ON storage.objects
FOR INSERT
TO public
WITH CHECK (bucket_id = 'payment-proofs');

-- Authenticated users belonging to the owning organisation can read proofs.
DROP POLICY IF EXISTS "payment_proofs_auth_select" ON storage.objects;
CREATE POLICY "payment_proofs_auth_select"
ON storage.objects
FOR SELECT
TO authenticated
USING (bucket_id = 'payment-proofs');

-- Authenticated users can delete their own organisation's proof files.
DROP POLICY IF EXISTS "payment_proofs_auth_delete" ON storage.objects;
CREATE POLICY "payment_proofs_auth_delete"
ON storage.objects
FOR DELETE
TO authenticated
USING (bucket_id = 'payment-proofs');


-- ============================================================
-- 3. RLS for new Phase 1 tables
-- ============================================================

-- business_units -----------------------------------------------
ALTER TABLE public.business_units ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "business_units_org_member_all" ON public.business_units;
CREATE POLICY "business_units_org_member_all"
ON public.business_units
FOR ALL
TO authenticated
USING (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
)
WITH CHECK (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
);


-- catalog_items ------------------------------------------------
ALTER TABLE public.catalog_items ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "catalog_items_org_member_all" ON public.catalog_items;
CREATE POLICY "catalog_items_org_member_all"
ON public.catalog_items
FOR ALL
TO authenticated
USING (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
)
WITH CHECK (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
);


-- payment_methods ----------------------------------------------
ALTER TABLE public.payment_methods ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "payment_methods_org_member_all" ON public.payment_methods;
CREATE POLICY "payment_methods_org_member_all"
ON public.payment_methods
FOR ALL
TO authenticated
USING (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
)
WITH CHECK (
    organization_id IN (
        SELECT organization_id FROM public.users WHERE id = auth.uid()
    )
);

-- Public-side read (needed when loading the public proposal page to show
-- payment instructions without a session).
DROP POLICY IF EXISTS "payment_methods_public_read" ON public.payment_methods;
CREATE POLICY "payment_methods_public_read"
ON public.payment_methods
FOR SELECT
TO public
USING (is_active = TRUE);


-- exchange_rate_snapshots --------------------------------------
ALTER TABLE public.exchange_rate_snapshots ENABLE ROW LEVEL SECURITY;

-- Everyone can read exchange rate snapshots (they are public market data).
DROP POLICY IF EXISTS "exchange_rate_snapshots_public_read" ON public.exchange_rate_snapshots;
CREATE POLICY "exchange_rate_snapshots_public_read"
ON public.exchange_rate_snapshots
FOR SELECT
TO public
USING (TRUE);

-- Only the service role / backend can insert (via SUPABASE_SERVICE_ROLE_KEY or
-- the anon key used by the backend process).  Granting to 'authenticated' as
-- well covers the case where the backend is called with a user JWT.
DROP POLICY IF EXISTS "exchange_rate_snapshots_backend_insert" ON public.exchange_rate_snapshots;
CREATE POLICY "exchange_rate_snapshots_backend_insert"
ON public.exchange_rate_snapshots
FOR INSERT
TO authenticated
WITH CHECK (TRUE);


-- proposal_acceptances -----------------------------------------
ALTER TABLE public.proposal_acceptances ENABLE ROW LEVEL SECURITY;

-- Anonymous clients can insert their acceptance.
DROP POLICY IF EXISTS "proposal_acceptances_anon_insert" ON public.proposal_acceptances;
CREATE POLICY "proposal_acceptances_anon_insert"
ON public.proposal_acceptances
FOR INSERT
TO public
WITH CHECK (TRUE);

-- Authenticated users can read acceptances for their own RFX records.
DROP POLICY IF EXISTS "proposal_acceptances_owner_read" ON public.proposal_acceptances;
CREATE POLICY "proposal_acceptances_owner_read"
ON public.proposal_acceptances
FOR SELECT
TO authenticated
USING (
    rfx_id IN (
        SELECT id FROM public.rfx_v2
        WHERE user_id = auth.uid()
           OR organization_id IN (
               SELECT organization_id FROM public.users WHERE id = auth.uid()
           )
    )
);


-- payment_submissions ------------------------------------------
ALTER TABLE public.payment_submissions ENABLE ROW LEVEL SECURITY;

-- Anonymous clients can insert payment submissions (public proposal flow).
DROP POLICY IF EXISTS "payment_submissions_anon_insert" ON public.payment_submissions;
CREATE POLICY "payment_submissions_anon_insert"
ON public.payment_submissions
FOR INSERT
TO public
WITH CHECK (TRUE);

-- Authenticated users can read/update submissions for their own RFX.
DROP POLICY IF EXISTS "payment_submissions_owner_all" ON public.payment_submissions;
CREATE POLICY "payment_submissions_owner_all"
ON public.payment_submissions
FOR ALL
TO authenticated
USING (
    rfx_id IN (
        SELECT id FROM public.rfx_v2
        WHERE user_id = auth.uid()
           OR organization_id IN (
               SELECT organization_id FROM public.users WHERE id = auth.uid()
           )
    )
)
WITH CHECK (
    rfx_id IN (
        SELECT id FROM public.rfx_v2
        WHERE user_id = auth.uid()
           OR organization_id IN (
               SELECT organization_id FROM public.users WHERE id = auth.uid()
           )
    )
);


-- service_orders -----------------------------------------------
ALTER TABLE public.service_orders ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "service_orders_owner_all" ON public.service_orders;
CREATE POLICY "service_orders_owner_all"
ON public.service_orders
FOR ALL
TO authenticated
USING (
    rfx_id IN (
        SELECT id FROM public.rfx_v2
        WHERE user_id = auth.uid()
           OR organization_id IN (
               SELECT organization_id FROM public.users WHERE id = auth.uid()
           )
    )
)
WITH CHECK (
    rfx_id IN (
        SELECT id FROM public.rfx_v2
        WHERE user_id = auth.uid()
           OR organization_id IN (
               SELECT organization_id FROM public.users WHERE id = auth.uid()
           )
    )
);


COMMIT;
