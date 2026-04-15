from aiokafka import AIOKafkaConsumer
from src.services.project_service import ProjectService


class ProfileKafkaConsumer:
    def __init__(
        self, consumer: AIOKafkaConsumer, profile_service: ProjectService
    ) -> None: ...

    async def start(self) -> None: ...
