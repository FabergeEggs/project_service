-- depends: 0005.create_denorm_user_table
CREATE TYPE project_status AS ENUM('ACTIVE', 'FINISHED', 'DELETED');

CREATE TABLE IF NOT EXISTS
    project (
        id UUID PRIMARY KEY,
        label VARCHAR(255) NOT NULL,
        short_description VARCHAR(500) NOT NULL,
        description VARCHAR(5000) NOT NULL,
        creator_id VARCHAR(255) NOT NULL,
        FOREIGN KEY (creator_id) REFERENCES denorm_user (id) ON DELETE RESTRICT,
        status project_status NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

CREATE INDEX IF NOT EXISTS idx_project_creator_id ON project (creator_id);