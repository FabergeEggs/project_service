from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService


class ProjectKafkaConsumer:
    def __init__(
        self, consumer: AIOKafkaConsumer, project_service: ProjectService
    ) -> None: ...

    async def start(self) -> None: ...
