-- One-off local dev seed so the team/checkpoint endpoints have something to
-- register against. Not part of the app's migrations on purpose.
INSERT INTO communities (id, slug, name_i18n, is_active, quorum_min_members, default_radius_m, max_accuracy_m, default_dwell_seconds, quorum_window_seconds)
VALUES (gen_random_uuid(), 'talat-phlu', '{"th":"ตลาดพลู","en":"Talat Phlu"}', true, 2, 40, 50, 45, 300)
ON CONFLICT (slug) DO NOTHING;
