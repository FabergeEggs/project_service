-- depends: 0001.create_project_table.sql
-- depends: 0007.create_tags_table.sql
CREATE TABLE IF NOT EXISTS
    project_tag_connection (
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        tag_id UUID NOT NULL,
        FOREIGN KEY (user_id) REFERENCES denorm_user (id) ON DELETE CASCADE,
        PRIMARY KEY (project_id, tag_id)
    )