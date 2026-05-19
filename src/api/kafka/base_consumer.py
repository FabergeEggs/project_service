# src/api/kafka/consumers/base_consumer.py
import asyncio
from abc import ABC, abstractmethod
from aiokafka import AIOKafkaConsumer
from loguru import logger


class BaseKafkaConsumer(ABC):
    def __init__(self, consumer: AIOKafkaConsumer):
        self._consumer = consumer

    async def start(self) -> None:
        await self._consumer.start()
        logger.info(f"{self.__class__.__name__} started")
        try:
            async for message in self._consumer:
                await self._handle_message(message)
        except asyncio.CancelledError:
            logger.info(f"{self.__class__.__name__} stopped")
        finally:
            await self._consumer.stop()

    @abstractmethod
    async def _handle_message(self, message) -> None:
        pass

    def _safe_get(self, event, *keys, default=None):
        for key in keys:
            if key in event:
                return event[key]
        return default
