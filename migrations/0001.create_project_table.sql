-- depends:
CREATE TYPE project_status AS ENUM('ACTIVE', 'FINISHED', 'DELETED');

CREATE TABLE IF NOT EXISTS
    project (
        id UUID PRIMARY KEY,
        label VARCHAR(255) NOT NULL,
        short_description VARCHAR(500) NOT NULL,
        description VARCHAR(5000) NOT NULL,
        creator VARCHAR(255) NOT NULL,
        status project_status NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );