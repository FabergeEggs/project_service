import asyncio
from abc import ABC, abstractmethod
from aiokafka import AIOKafkaConsumer
from loguru import logger


class BaseKafkaConsumer(ABC):
    """
    Abstract base class for Kafka consumers.

    Handles consumer lifecycle management including starting, message processing loop,
    and graceful shutdown. Subclasses must implement _handle_message() method.
    """

    def __init__(self, consumer: AIOKafkaConsumer):
        """
        Initialize the base consumer with a Kafka consumer instance.

        Args:
            consumer: Configured AIOKafkaConsumer instance.
        """
        self._consumer = consumer

    async def start(self) -> None:
        """
        Start the consumer and begin processing messages.

        Starts the consumer, enters the message processing loop, and handles
        graceful shutdown on CancelledError. Each received message is passed
        to the abstract _handle_message() method for processing.

        The consumer continues running until cancelled.
        """
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
        """
        Process a single Kafka message.

        This method must be implemented by subclasses to handle
        specific message types and business logic.

        Args:
            message: Raw Kafka message object with value, key, etc.
        """
        pass

    def _safe_get(self, event, *keys, default=None):
        """
        Safely retrieve nested values from an event dictionary.

        Tries each key in order and returns the value of the first key
        found in the event dictionary.

        Args:
            event: Dictionary containing event data.
            *keys: Variable number of key strings to try in order.
            default: Default value to return if none of the keys are found.

        Returns:
            Value of the first found key, or default if none found.
        """
        for key in keys:
            if key in event:
                return event[key]
        return default
