-- depends: 0001.create_project_table.sql
-- depends: 0005.create_denorm_user_table.sql
CREATE TYPE project_role AS ENUM('scientist', 'volunteer', 'deleted');

CREATE TABLE IF NOT EXISTS
    project_user_connection (
        id SERIAL PRIMARY KEY,
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        user_id UUID NOT NULL,
        FOREIGN KEY (user_id) REFERENCES denorm_user (id) ON DELETE CASCADE,
        PRIMARY KEY (project_id, user_id),
        joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status project_role NOT NULL
    )