-- depends:
CREATE TABLE IF NOT EXISTS
    tags (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        count INTEGER NOT NULL
    );