-- One-off local dev seed for a couple of test checkpoints (two, so there's
-- both a completed and a not-yet-completed marker to check the map against).
INSERT INTO checkpoints (id, community_id, sequence, slug, name_i18n, content_i18n, lat, lng, is_active)
SELECT gen_random_uuid(), id, 1, 'wat-arun', '{"th":"วัดอรุณ","en":"Wat Arun"}', '{}', 13.7437, 100.4888, true
FROM communities WHERE slug = 'talat-phlu'
ON CONFLICT (community_id, slug) DO NOTHING;

INSERT INTO checkpoints (id, community_id, sequence, slug, name_i18n, content_i18n, lat, lng, is_active)
SELECT gen_random_uuid(), id, 2, 'wat-pho', '{"th":"วัดโพธิ์","en":"Wat Pho"}', '{}', 13.7468, 100.4930, true
FROM communities WHERE slug = 'talat-phlu'
ON CONFLICT (community_id, slug) DO NOTHING;
