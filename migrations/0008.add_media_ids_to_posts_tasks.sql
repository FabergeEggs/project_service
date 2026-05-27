-- depends: 0002.create_post_table
-- depends: 0003.create_task_table
ALTER TABLE post ADD COLUMN IF NOT EXISTS media_ids UUID[] NOT NULL DEFAULT '{}';
ALTER TABLE task ADD COLUMN IF NOT EXISTS media_ids UUID[] NOT NULL DEFAULT '{}';
