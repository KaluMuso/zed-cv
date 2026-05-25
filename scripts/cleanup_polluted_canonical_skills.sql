-- Remove sentence-like rows from canonical_skills (run in Supabase SQL editor).
-- Review the SELECT result before executing DELETE.
-- job_skills rows referencing deleted canonical IDs cascade per FK rules.

-- Identify polluted rows (sentences, not skills)
SELECT id, name
FROM canonical_skills
WHERE length(name) > 60
   OR name ~ '(Years|Experience|Minimum|Must|Should|Required|Bachelor|Diploma|Certificate|Membership|Knowledge of|Ability to)'
   OR name LIKE '%.';

-- Count rows that would be deleted (run before DELETE)
SELECT COUNT(*) AS polluted_row_count
FROM canonical_skills
WHERE length(name) > 60
   OR name ~ '(Years|Experience|Minimum|Must|Should|Required|Bachelor|Diploma|Certificate)'
   OR name LIKE '%.';

-- After review, delete them (cascades to job_skills referencing these IDs)
DELETE FROM canonical_skills
WHERE length(name) > 60
   OR name ~ '(Years|Experience|Minimum|Must|Should|Required|Bachelor|Diploma|Certificate)'
   OR name LIKE '%.';

-- Post-cleanup sanity checks
SELECT COUNT(*) AS names_longer_than_40
FROM canonical_skills
WHERE length(name) > 40;

SELECT name
FROM canonical_skills
ORDER BY length(name) DESC
LIMIT 20;
