BEGIN;

ALTER TABLE public.product_catalog
    ADD COLUMN IF NOT EXISTS business_unit_id UUID REFERENCES public.business_units(id) ON DELETE SET NULL;

COMMENT ON COLUMN public.product_catalog.business_unit_id IS
    'Nullable business-unit scope. NULL means the product is intentionally shared organization-wide.';

CREATE INDEX IF NOT EXISTS idx_product_catalog_org_business_unit_active
    ON public.product_catalog (organization_id, business_unit_id, is_active);

CREATE INDEX IF NOT EXISTS idx_product_catalog_user_business_unit_active
    ON public.product_catalog (user_id, business_unit_id, is_active);

CREATE OR REPLACE FUNCTION public.bootstrap_default_business_unit_for_organization()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
DECLARE
    resolved_slug TEXT;
BEGIN
    IF EXISTS (
        SELECT 1
        FROM public.business_units bu
        WHERE bu.organization_id = NEW.id
    ) THEN
        RETURN NEW;
    END IF;

    resolved_slug := COALESCE(
        NULLIF(NEW.slug, ''),
        regexp_replace(lower(NEW.name), '[^a-z0-9]+', '-', 'g')
    );

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
    VALUES (
        NEW.id,
        NEW.name,
        resolved_slug,
        'Default business unit created automatically during organization bootstrap',
        'services',
        NEW.name,
        TRUE,
        TRUE
    )
    ON CONFLICT (organization_id, slug) DO NOTHING;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bootstrap_default_business_unit ON public.organizations;

CREATE TRIGGER trg_bootstrap_default_business_unit
AFTER INSERT ON public.organizations
FOR EACH ROW
EXECUTE FUNCTION public.bootstrap_default_business_unit_for_organization();

UPDATE public.business_units
SET industry_context = 'corporate_catering'
WHERE lower(name) = 'bizbites'
  AND lower(COALESCE(industry_context, 'services')) = 'services';

UPDATE public.business_units
SET industry_context = 'food_safety_testing'
WHERE lower(name) = 'sil prove'
  AND lower(COALESCE(industry_context, 'services')) = 'services';

UPDATE public.business_units
SET industry_context = 'industrial_food_management'
WHERE lower(name) = 'sabra ifm'
  AND lower(COALESCE(industry_context, 'services')) = 'services';

COMMIT;
