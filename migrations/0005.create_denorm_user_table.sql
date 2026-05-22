-- depends:
CREATE TABLE IF NOT EXISTS
    denorm_user (
        id UUID PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        avatar_url VARCHAR(255) NOT NULL
    );