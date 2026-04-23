SELECT COUNT(*) FROM wired_articles;
SELECT title, author FROM wired_articles LIMIT 5;


-- ================================================
-- queries.sql — 3 Query Wajib Wired Articles
-- ================================================

-- QUERY 1: Title dan author yang sudah bersih (tanpa kata "By")
-- Transformasi sudah dilakukan di Prefect flow,
-- tapi kita tambahkan REGEXP_REPLACE sebagai safety net
SELECT title, REGEXP_REPLACE(author, '^[Bb]y\s+', '') AS author_clean
FROM wired_articles
ORDER BY title;


-- QUERY 2: 3 penulis yang paling sering muncul
SELECT author, COUNT(*) AS jumlah_artikel
FROM wired_articles
WHERE author IS NOT NULL AND author <> ''
GROUP BY author
ORDER BY jumlah_artikel DESC
LIMIT 3;


-- QUERY 3: Artikel yang mengandung kata kunci "AI", "Climate", atau "Security"
-- di title atau description (case-insensitive)
SELECT title, author, description
FROM wired_articles
WHERE title        ILIKE '%AI%'
    OR title        ILIKE '%Climate%'
    OR title        ILIKE '%Security%'
    OR description  ILIKE '%AI%'
    OR description  ILIKE '%Climate%'
    OR description  ILIKE '%Security%'
ORDER BY title;