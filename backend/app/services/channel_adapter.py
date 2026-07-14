from datetime import UTC, datetime


def utcnow_millis() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


class MockChannelAdapter:
    async def send_message(self, *, channel: str, recipient: str, body: str) -> str:
        # Deterministic enough id for local test runs.
        return f"{channel}-{recipient}-{utcnow_millis()}"


_adapter = MockChannelAdapter()


def get_channel_adapter() -> MockChannelAdapter:
    return _adapter


def set_channel_adapter(adapter) -> None:
    global _adapter
    _adapter = adapter
