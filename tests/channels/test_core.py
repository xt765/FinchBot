import pytest
import asyncio
from finchbot.channels.schema import InboundMessage, OutboundMessage
from finchbot.channels.bus import MessageBus
from finchbot.channels.base import BaseChannel
from finchbot.channels.manager import ChannelManager

class MockChannel(BaseChannel):
    name = "mock"
    def __init__(self, config, bus):
        super().__init__(config, bus)
        self.sent_messages = []
        self.started = False
        self.stopped = False

    async def start(self):
        self.started = True
        # Keep running
        while self.started:
            await asyncio.sleep(0.1)

    async def stop(self):
        self.started = False
        self.stopped = True

    async def send(self, msg: OutboundMessage):
        self.sent_messages.append(msg)

@pytest.mark.asyncio
async def test_message_bus():
    bus = MessageBus()
    
    in_msg = InboundMessage(channel="mock", sender_id="u1", chat_id="c1", content="hello")
    await bus.publish_inbound(in_msg)
    
    received = await bus.consume_inbound()
    assert received == in_msg
    
    out_msg = OutboundMessage(target_channel="mock", target_id="c1", content="world")
    await bus.publish_outbound(out_msg)
    
    received_out = await bus.consume_outbound()
    assert received_out == out_msg

@pytest.mark.asyncio
async def test_channel_manager():
    bus = MessageBus()
    manager = ChannelManager(config={}, bus=bus)
    
    mock_channel = MockChannel(config={}, bus=bus)
    manager.register_channel("mock", mock_channel)
    
    # Start
    await manager.start_all()
    await asyncio.sleep(0.1) # Let tasks start
    assert mock_channel.started
    
    # Test Dispatch
    out_msg = OutboundMessage(target_channel="mock", target_id="c1", content="hi")
    await bus.publish_outbound(out_msg)
    
    # Wait for dispatcher to pick it up
    for _ in range(10):
        if len(mock_channel.sent_messages) > 0:
            break
        await asyncio.sleep(0.1)
    
    assert len(mock_channel.sent_messages) == 1
    assert mock_channel.sent_messages[0].content == "hi"
    
    # Stop
    await manager.stop_all()
    assert mock_channel.stopped
