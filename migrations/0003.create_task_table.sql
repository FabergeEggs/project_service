-- depends: 0001.create_project_table.sql
CREATE TYPE task_status AS ENUM('active', 'finished', 'deleted');

CREATE TABLE IF NOT EXISTS
    task (
        id UUID PRIMARY KEY,
        project_id UUID NOT NULL,
        FOREIGN KEY (project_id) REFERENCES project (id) ON DELETE CASCADE,
        label VARCHAR(255) NOT NULL,
        short_description VARCHAR(500) NOT NULL,
        description VARCHAR(5000) NOT NULL,
        creator VARCHAR(255) NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        status task_status NOT NULL
    )