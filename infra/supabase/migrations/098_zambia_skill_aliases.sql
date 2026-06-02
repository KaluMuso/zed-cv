-- 098: Zambia job-market skill aliases (CV parser + matching normalization).

BEGIN;

INSERT INTO public.skills (name, category) VALUES
    ('sage', 'tool'),
    ('pastel', 'tool'),
    ('quickbooks', 'tool'),
    ('xero', 'tool'),
    ('teamwork', 'soft'),
    ('inventory management', 'domain'),
    ('accounts payable', 'domain'),
    ('accounts receivable', 'domain'),
    ('computer literacy', 'domain'),
    ('information technology', 'domain')
ON CONFLICT (name) DO NOTHING;

INSERT INTO public.skill_aliases (alias, skill_id) VALUES
    ('sage 300', (SELECT id FROM skills WHERE name = 'sage')),
    ('sage pastel', (SELECT id FROM skills WHERE name = 'pastel')),
    ('pastel accounting', (SELECT id FROM skills WHERE name = 'pastel')),
    ('pastel partner', (SELECT id FROM skills WHERE name = 'pastel')),
    ('qb', (SELECT id FROM skills WHERE name = 'quickbooks')),
    ('quick books', (SELECT id FROM skills WHERE name = 'quickbooks')),
    ('ms office', (SELECT id FROM skills WHERE name = 'microsoft office')),
    ('office suite', (SELECT id FROM skills WHERE name = 'microsoft office')),
    ('office 365', (SELECT id FROM skills WHERE name = 'microsoft office')),
    ('computer literate', (SELECT id FROM skills WHERE name = 'computer literacy')),
    ('computer skills', (SELECT id FROM skills WHERE name = 'computer literacy')),
    ('ict', (SELECT id FROM skills WHERE name = 'information technology')),
    ('it', (SELECT id FROM skills WHERE name = 'information technology')),
    ('team player', (SELECT id FROM skills WHERE name = 'teamwork')),
    ('team work', (SELECT id FROM skills WHERE name = 'teamwork')),
    ('interpersonal skills', (SELECT id FROM skills WHERE name = 'communication')),
    ('people skills', (SELECT id FROM skills WHERE name = 'communication')),
    ('stock control', (SELECT id FROM skills WHERE name = 'inventory management')),
    ('stock management', (SELECT id FROM skills WHERE name = 'inventory management')),
    ('debtors', (SELECT id FROM skills WHERE name = 'accounts receivable')),
    ('creditors', (SELECT id FROM skills WHERE name = 'accounts payable')),
    ('ap', (SELECT id FROM skills WHERE name = 'accounts payable')),
    ('ar', (SELECT id FROM skills WHERE name = 'accounts receivable')),
    ('financial management', (SELECT id FROM skills WHERE name = 'accounting')),
    ('book keeping', (SELECT id FROM skills WHERE name = 'bookkeeping')),
    ('book-keeping', (SELECT id FROM skills WHERE name = 'bookkeeping')),
    ('customer care', (SELECT id FROM skills WHERE name = 'customer service')),
    ('client service', (SELECT id FROM skills WHERE name = 'customer service')),
    ('driving license', (SELECT id FROM skills WHERE name = 'driving')),
    ('drivers license', (SELECT id FROM skills WHERE name = 'driving')),
    ('class 1 license', (SELECT id FROM skills WHERE name = 'driving')),
    ('class 2 license', (SELECT id FROM skills WHERE name = 'driving')),
    ('forklift operator', (SELECT id FROM skills WHERE name = 'forklift')),
    ('reach truck', (SELECT id FROM skills WHERE name = 'forklift')),
    ('procurement officer', (SELECT id FROM skills WHERE name = 'procurement')),
    ('supply chain management', (SELECT id FROM skills WHERE name = 'supply chain')),
    ('hr management', (SELECT id FROM skills WHERE name = 'human resources')),
    ('human resource', (SELECT id FROM skills WHERE name = 'human resources')),
    ('sales marketing', (SELECT id FROM skills WHERE name = 'marketing')),
    ('digital marketing', (SELECT id FROM skills WHERE name = 'marketing')),
    ('social media marketing', (SELECT id FROM skills WHERE name = 'marketing')),
    ('event planning', (SELECT id FROM skills WHERE name = 'planning')),
    ('events management', (SELECT id FROM skills WHERE name = 'planning')),
    ('project mgmt', (SELECT id FROM skills WHERE name = 'project management')),
    ('prince2', (SELECT id FROM skills WHERE name = 'project management'))
ON CONFLICT (alias) DO NOTHING;

COMMIT;
