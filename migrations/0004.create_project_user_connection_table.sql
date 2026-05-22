-- depends: 0001.create_project_table
-- depends: 0005.create_denorm_user_table
CREATE TYPE project_role AS ENUM('SCIENTIST', 'VOLUNTEER', 'DELETED');

CREATE TABLE IF NOT EXISTS
    project_user_connection (
        project_id UUID NOT NULL,
        user_id UUID NOT NULL,
        role project_role NOT NULL DEFAULT 'VOLUNTEER',
        joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (project_id, user_id),
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES denorm_user (id) ON DELETE CASCADE
    );

CREATE INDEX IF NOT EXISTS idx_project_user_connection_user_id ON project_user_connection (user_id);