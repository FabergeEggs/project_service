-- depends: 0001.create_project_table
-- depends: 0005.create_denorm_user_table
CREATE TYPE task_status AS ENUM('ACTIVE', 'FINISHED', 'DELETED');

CREATE TABLE IF NOT EXISTS
    task (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        label VARCHAR(255) NOT NULL,
        short_description VARCHAR(500) NOT NULL,
        description VARCHAR(5000) NOT NULL,
        creator_id UUID NOT NULL,
        FOREIGN KEY (creator_id) REFERENCES denorm_user (id) ON DELETE RESTRICT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status task_status NOT NULL,
        answer_count INTEGER NOT NULL DEFAULT 0
    );

CREATE INDEX IF NOT EXISTS idx_task_project_id ON task (project_id);