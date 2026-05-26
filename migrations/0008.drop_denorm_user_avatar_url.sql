-- depends: 0007.create_tags_table
ALTER TABLE denorm_user DROP COLUMN IF EXISTS avatar_url;
