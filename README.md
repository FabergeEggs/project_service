# Project Service

Project service repository that implement projects and all their functional: tasks, posts and memberships that it include. Work as a part in the infrstructure repository with single docker compose.

Project use FastAPI for router, PostgreSQL as database, so implementation of the infrstructure layer use row SQL requests to it.

## Project structure

<pre>
.
├─ migrations
│  ├─ 0001.create_project_table.rollback.sql
│  ├─ 0001.create_project_table.sql
│  ├─ 0002.create_post_table.rollback.sql
│  ├─ 0002.create_post_table.sql
│  ├─ 0003.create_task_table.rollback.sql
│  ├─ 0003.create_task_table.sql
│  ├─ 0004.create_project_user_connection_table.rollback.sql
│  ├─ 0004.create_project_user_connection_table.sql
│  ├─ 0005.create_denorm_user_table.rollback.sql
│  ├─ 0005.create_denorm_user_table.sql
│  ├─ 0006.create_project_tag_connection_table.rollback.sql
│  ├─ 0006.create_project_tag_connection_table.sql
│  ├─ 0007.create_tags_table.rollback.sql
│  ├─ 0007.create_tags_table.sql
│  ├─ migrate.py
│  └─ __init__.py
├─ src
│  ├─ adapters
│  │  ├─ clients
│  │  │  ├─ kafka_producer.py
│  │  │  └─ __init__.py
│  │  ├─ repository
│  │  │  ├─ postgres
│  │  │  │  ├─ project_repository.py
│  │  │  │  ├─ queries.py
│  │  │  │  └─ __init__.py
│  │  │  ├─ errors.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ api
│  │  ├─ http
│  │  │  ├─ dependencies.py
│  │  │  ├─ dto.py
│  │  │  ├─ project_router.py
│  │  │  └─ __init__.py
│  │  ├─ kafka
│  │  │  ├─ answer_consumer.py
│  │  │  ├─ base_consumer.py
│  │  │  ├─ comments_consumer.py
│  │  │  ├─ profile_consumer.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  ├─ models
│  │  ├─ project.py
│  │  └─ __init__.py
│  ├─ services
│  │  ├─ errors.py
│  │  ├─ project_service.py
│  │  ├─ protocols.py
│  │  └─ __init__.py
│  ├─ config.py
│  ├─ main.py
│  └─ __init__.py
├─ tests
│  ├─ integration
│  │  ├─ adapters
│  │  │  ├─ repository
│  │  │  │  ├─ test_project.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ api
│  │  ├─ conftest.py
│  │  └─ __init__.py
│  ├─ unit
│  │  ├─ api
│  │  │  ├─ http
│  │  │  │  ├─ test_router.py
│  │  │  │  └─ __init__.py
│  │  │  └─ __init__.py
│  │  ├─ service
│  │  │  ├─ test_post.py
│  │  │  ├─ test_project.py
│  │  │  ├─ test_publications.py
│  │  │  ├─ test_task.py
│  │  │  ├─ test_user.py
│  │  │  └─ __init__.py
│  │  └─ __init__.py
│  └─ __init__.py
├─ uv.lock
├─ .dockerignore
├─ docker-compose.yaml
├─ Dockerfile
├─ mypy.ini
├─ pyproject.toml
├─ README.md
├─ requirements-dev.txt
├─ requirements.txt
└─ yoyo.ini
</pre>

## API

### Health & Utility Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/project/health` | Health check endpoint for service monitoring |

### Project Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/project` | Create a new project | Required |
| GET | `/project/{project_id}/info` | Get detailed information about a specific project | - |
| GET | `/project/{project_id}/statistics` | Get aggregated statistics (tasks, participants, answers) | - |
| PUT | `/project/{project_id}` | Update an existing project | Required |
| POST | `/project/batch` | Retrieve multiple projects by IDs | - |

### Task Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/project/{project_id}/task` | Create a new task within a project | Required |
| GET | `/project/{project_id}/task/{task_id}` | Get detailed information about a specific task | - |
| PUT | `/project/{project_id}/task/{task_id}` | Update an existing task | Required |

### Post Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/project/{project_id}/post` | Create a new post within a project | Required |
| GET | `/project/{project_id}/post/{post_id}` | Get detailed information about a specific post | - |
| PUT | `/project/{project_id}/post/{post_id}` | Update an existing post | Required |
| DELETE | `/project/{project_id}/post/{post_id}` | Delete a post | Required |

### Membership Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/project/{project_id}/member` | Add a user as a member to a project | Required |
| DELETE | `/project/{project_id}/member/{user_id}` | Remove a user from a project membership | Required |

### Publications & Profile Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/project/{project_id}/publications` | Get paginated publications (posts/tasks) for a project with cursor-based pagination | - |
| GET | `/project/profile/{profile_id}` | Get all project memberships for a specific user profile | - |

## Database Schema

### Tables

#### `denorm_user`
Denormalized user information synchronized from the authentication service.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `name` | VARCHAR(255) | NOT NULL |
| `avatar_url` | VARCHAR(255) | NOT NULL |

#### `project`
Core project entity containing project metadata and status.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `label` | VARCHAR(255) | NOT NULL |
| `short_description` | VARCHAR(500) | NOT NULL |
| `description` | VARCHAR(5000) | NOT NULL |
| `creator_id` | UUID | NOT NULL, FK → denorm_user(id) |
| `status` | ENUM('ACTIVE', 'FINISHED', 'DELETED') | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Indexes:** `idx_project_creator_id` on creator_id

#### `post`
Posts created within projects for communication and announcements.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `project_id` | UUID | NOT NULL, FK → project(id) ON DELETE CASCADE |
| `label` | VARCHAR(255) | NOT NULL |
| `short_description` | VARCHAR(500) | NOT NULL |
| `description` | VARCHAR(5000) | NOT NULL |
| `creator_id` | UUID | NOT NULL, FK → denorm_user(id) ON DELETE RESTRICT |
| `comments_count` | INTEGER | NOT NULL, DEFAULT 0 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Indexes:** `idx_post_project_id` on project_id

#### `task`
Tasks created within projects for collaborative work and problem-solving.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `project_id` | UUID | NOT NULL, FK → project(id) ON DELETE CASCADE |
| `label` | VARCHAR(255) | NOT NULL |
| `short_description` | VARCHAR(500) | NOT NULL |
| `description` | VARCHAR(5000) | NOT NULL |
| `creator_id` | UUID | NOT NULL, FK → denorm_user(id) ON DELETE RESTRICT |
| `status` | ENUM('ACTIVE', 'FINISHED', 'DELETED') | NOT NULL |
| `answer_count` | INTEGER | NOT NULL, DEFAULT 0 |
| `created_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |
| `updated_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Indexes:** `idx_task_project_id` on project_id

#### `tags`
Tags for categorizing and organizing projects.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PRIMARY KEY |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE |
| `count` | INTEGER | NOT NULL |

#### `project_tag_connection`
Junction table linking projects to tags for many-to-many relationship.

| Column | Type | Constraints |
|--------|------|-------------|
| `project_id` | UUID | NOT NULL, FK → project(id) ON DELETE CASCADE |
| `tag_id` | UUID | NOT NULL, FK → tags(id) ON DELETE CASCADE |

**Primary Key:** (project_id, tag_id)
**Indexes:** `idx_project_tag_connection_tag_id` on project_id

#### `project_user_connection`
Junction table linking users to projects with role assignments.

| Column | Type | Constraints |
|--------|------|-------------|
| `project_id` | UUID | NOT NULL, FK → project(id) ON DELETE CASCADE |
| `user_id` | UUID | NOT NULL, FK → denorm_user(id) ON DELETE CASCADE |
| `role` | ENUM('SCIENTIST', 'VOLUNTEER', 'DELETED') | NOT NULL, DEFAULT 'VOLUNTEER' |
| `joined_at` | TIMESTAMPTZ | NOT NULL, DEFAULT NOW() |

**Primary Key:** (project_id, user_id)
**Indexes:** `idx_project_user_connection_user_id` on user_id

### Data Model Relationships

```
denorm_user
    ├── (creator_id) → project
    ├── (creator_id) → post
    ├── (creator_id) → task
    └── (user_id) ← project_user_connection → (project_id) ← project

project
    ├── (id) → post
    ├── (id) → task
    ├── (id) ← project_tag_connection → (tag_id) ← tags
    └── (id) ← project_user_connection → (user_id) ← denorm_user
```