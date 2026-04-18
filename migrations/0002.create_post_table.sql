-- depends: 0001.create_project_table
-- depends: 0005.create_denorm_user_table
CREATE TABLE IF NOT EXISTS
    post (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        label VARCHAR(255) NOT NULL,
        short_description VARCHAR(500) NOT NULL,
        description VARCHAR(5000) NOT NULL,
        creator_id VARCHAR(255) NOT NULL,
        FOREIGN KEY (creator_id) REFERENCES denorm_user (id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )