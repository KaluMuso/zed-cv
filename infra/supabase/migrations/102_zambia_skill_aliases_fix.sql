-- 102: Repair 098 when it failed on NULL skill_id (parent skills missing).
-- Idempotent — safe if 098 already succeeded after the 098 file fix.

BEGIN;

INSERT INTO public.skills (name, category) VALUES
    ('sage', 'tool'),
    ('pastel', 'tool'),
    ('quickbooks', 'tool'),
    ('xero', 'tool'),
    ('teamwork', 'soft_skill'),
    ('inventory management', 'domain'),
    ('accounts payable', 'domain'),
    ('accounts receivable', 'domain'),
    ('computer literacy', 'domain'),
    ('information technology', 'domain'),
    ('bookkeeping', 'domain'),
    ('driving', 'domain'),
    ('forklift', 'domain'),
    ('procurement', 'domain'),
    ('planning', 'domain')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.skill_aliases (alias, skill_id)
SELECT v.alias, s.id
FROM (
    VALUES
        ('sage 300', 'sage'),
        ('sage pastel', 'pastel'),
        ('pastel accounting', 'pastel'),
        ('pastel partner', 'pastel'),
        ('qb', 'quickbooks'),
        ('quick books', 'quickbooks'),
        ('ms office', 'microsoft office'),
        ('office suite', 'microsoft office'),
        ('office 365', 'microsoft office'),
        ('computer literate', 'computer literacy'),
        ('computer skills', 'computer literacy'),
        ('ict', 'information technology'),
        ('it', 'information technology'),
        ('team player', 'teamwork'),
        ('team work', 'teamwork'),
        ('interpersonal skills', 'communication'),
        ('people skills', 'communication'),
        ('stock control', 'inventory management'),
        ('stock management', 'inventory management'),
        ('debtors', 'accounts receivable'),
        ('creditors', 'accounts payable'),
        ('ap', 'accounts payable'),
        ('ar', 'accounts receivable'),
        ('financial management', 'accounting'),
        ('book keeping', 'bookkeeping'),
        ('book-keeping', 'bookkeeping'),
        ('customer care', 'customer service'),
        ('client service', 'customer service'),
        ('driving license', 'driving'),
        ('drivers license', 'driving'),
        ('class 1 license', 'driving'),
        ('class 2 license', 'driving'),
        ('forklift operator', 'forklift'),
        ('reach truck', 'forklift'),
        ('procurement officer', 'procurement'),
        ('supply chain management', 'supply chain'),
        ('hr management', 'human resources'),
        ('human resource', 'human resources'),
        ('sales marketing', 'marketing'),
        ('digital marketing', 'marketing'),
        ('social media marketing', 'marketing'),
        ('event planning', 'planning'),
        ('events management', 'planning'),
        ('project mgmt', 'project management'),
        ('prince2', 'project management')
) AS v(alias, skill_name)
INNER JOIN public.skills s ON s.name = v.skill_name
ON CONFLICT (alias) DO NOTHING;

COMMIT;
