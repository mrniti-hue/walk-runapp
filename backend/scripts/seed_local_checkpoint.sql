-- One-off local dev seed for a single test checkpoint.
INSERT INTO checkpoints (id, community_id, sequence, slug, name_i18n, content_i18n, lat, lng, is_active)
SELECT gen_random_uuid(), id, 1, 'wat-arun', '{"th":"วัดอรุณ","en":"Wat Arun"}', '{}', 13.7437, 100.4888, true
FROM communities WHERE slug = 'talat-phlu'
ON CONFLICT (community_id, slug) DO NOTHING;
