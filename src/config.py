from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8")

    database_dsn: str = Field(
        default="postgresql://user:password@localhost:5432/project_db",
        alias="DATABASE_DSN",
    )
    database_min_connections: int = Field(
        default=1, alias="DATABASE_MIN_CONNECTIONS")
    database_max_connections: int = Field(
        default=10, alias="DATABASE_MAX_CONNECTIONS")
    kafka_bootstrap: str = Field(
        default="localhost:9093", alias="KAFKA_BOOTSTRAP")
    kafka_topic_answers: str = Field(
        default="project-answers", alias="KAFKA_TOPIC_ANSWERS"
    )  # response_service publishes answer.created / answer.deleted here
    kafka_topic_comments: str = Field(
        default="project-comments", alias="KAFKA_TOPIC_COMMENTS"
    )
    kafka_topic_events: str = Field(
        default="project-events", alias="KAFKA_TOPIC_EVENTS")
    kafka_group_id: str = Field(
        default="project-service", alias="KAFKA_GROUP_ID")
    http_host: str = Field(default="0.0.0.0", alias="HTTP_HOST")
    http_port: int = Field(default=8003, alias="HTTP_PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
