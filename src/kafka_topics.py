"""Canonical Kafka topic names for cross-service integration."""

# Outbound — consumed by response_service
TASK_CREATED = "project_service.task.created"
TASK_CHANGED = "project_service.task.changed"
TASK_DELETE = "project_service.task.delete"
POST_CREATED = "project_service.post.created"
POST_CHANGED = "project_service.post.changed"
POST_DELETE = "project_service.post.delete"

# Inbound — from response_service (answer counters)
ANSWERS = "project-answers"

# Inbound — from profile_service
PROFILE_USER_REGISTERED = "profile_service.user.registered"
PROFILE_CHANGED = "profile_service.profile.changed"
PROFILE_USER_DELETED = "profile_service.user.deleted"

PROFILE_TOPICS = [
    PROFILE_USER_REGISTERED,
    PROFILE_CHANGED,
    PROFILE_USER_DELETED,
]
