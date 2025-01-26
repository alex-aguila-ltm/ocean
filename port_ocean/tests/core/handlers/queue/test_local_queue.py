import asyncio
import pytest
from dataclasses import dataclass

from port_ocean.core.handlers.queue.local_queue import LocalQueue


@dataclass
class TestMessage:
    """Example message type for testing."""

    id: str
    data: str
    processed: bool = False


class TestLocalQueue:
    """
    Test suite for LocalQueue implementation.
    This can serve as an example for testing other Queue implementations.
    """

    @pytest.fixture
    def queue(self) -> LocalQueue[TestMessage]:
        return LocalQueue[TestMessage]()

    async def test_basic_queue_operations(self, queue: LocalQueue[TestMessage]) -> None:
        """Test basic put/get operations."""
        message = TestMessage(id="1", data="test")

        # Put item in queue
        await queue.put(message)

        # Get item from queue
        received = await queue.get()

        assert received.id == message.id
        assert received.data == message.data

        # Mark as processed
        await queue.commit()

    async def test_fifo_order(self, queue: LocalQueue[TestMessage]) -> None:
        """Demonstrate and test FIFO (First In, First Out) behavior."""
        messages = [
            TestMessage(id="1", data="first"),
            TestMessage(id="2", data="second"),
            TestMessage(id="3", data="third"),
        ]

        # Put items in queue
        for msg in messages:
            await queue.put(msg)

        # Verify order
        for expected in messages:
            received = await queue.get()
            assert received.id == expected.id
            await queue.commit()

    async def test_wait_for_completion(self, queue: LocalQueue[TestMessage]) -> None:
        """Example of waiting for all messages to be processed."""
        processed_count = 0

        async def slow_processor() -> None:
            nonlocal processed_count
            while True:
                try:
                    await asyncio.wait_for(queue.get(), timeout=0.1)
                    # Simulate processing time
                    await asyncio.sleep(0.1)
                    processed_count += 1
                    await queue.commit()
                except asyncio.TimeoutError:
                    break

        # Add messages
        message_count = 5
        for i in range(message_count):
            await queue.put(TestMessage(id=str(i), data=f"test_{i}"))

        # Start processor
        processor = asyncio.create_task(slow_processor())

        # Wait for completion
        await queue.wait_for_all_items_to_be_complete()

        await processor

        assert processed_count == message_count
