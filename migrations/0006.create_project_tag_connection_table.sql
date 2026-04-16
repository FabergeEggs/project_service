-- depends: 0001.create_project_table
-- depends: 0007.create_tags_table
CREATE TABLE IF NOT EXISTS
    project_tag_connection (
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        tag_id UUID NOT NULL,
        FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
        PRIMARY KEY (project_id, tag_id)
    )