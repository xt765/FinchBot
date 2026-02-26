import asyncio
import json
import sqlite3
from pathlib import Path

from loguru import logger

from .schema import InboundMessage, OutboundMessage


class PersistentMessageBus:
    """
    Async message bus with SQLite persistence.

    Features:
    - Message persistence for recovery after restart
    - Message acknowledgment
    - Dead letter queue for failed messages
    - Priority queue support
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
        self._pending_acks: dict[str, InboundMessage] = {}
        self._lock = asyncio.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database for message persistence."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inbound_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                channel TEXT NOT NULL,
                sender_id TEXT NOT NULL,
                chat_id TEXT NOT NULL,
                content TEXT NOT NULL,
                media TEXT,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS outbound_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT UNIQUE,
                target_channel TEXT NOT NULL,
                target_id TEXT NOT NULL,
                content TEXT NOT NULL,
                files TEXT,
                reply_to TEXT,
                metadata TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dead_letter_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_type TEXT NOT NULL,
                message_data TEXT NOT NULL,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inbound_status ON inbound_messages(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_outbound_status ON outbound_messages(status)')

        conn.commit()
        conn.close()

    async def publish_inbound(self, msg: InboundMessage) -> str:
        """Publish a message from a channel to the agent with persistence."""
        import uuid
        message_id = str(uuid.uuid4())

        await self._persist_inbound(message_id, msg)

        self._pending_acks[message_id] = msg

        await self.inbound.put(msg)
        logger.debug(f"Bus inbound: {msg.session_key} - {msg.content[:50]}...")

        return message_id

    async def _persist_inbound(self, message_id: str, msg: InboundMessage):
        """Persist inbound message to database."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._persist_inbound_sync,
            message_id,
            msg
        )

    def _persist_inbound_sync(self, message_id: str, msg: InboundMessage):
        """Synchronous persistence of inbound message."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO inbound_messages
                (message_id, channel, sender_id, chat_id, content, media, metadata, timestamp, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                msg.channel,
                msg.sender_id,
                msg.chat_id,
                msg.content,
                json.dumps(msg.media),
                json.dumps(msg.metadata),
                msg.timestamp.isoformat(),
                'pending'
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    async def ack_inbound(self, message_id: str):
        """Acknowledge successful processing of a message."""
        async with self._lock:
            if message_id in self._pending_acks:
                del self._pending_acks[message_id]

        await self._update_inbound_status(message_id, 'processed')

    async def _update_inbound_status(self, message_id: str, status: str):
        """Update message status in database."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._update_status_sync,
            'inbound_messages',
            message_id,
            status
        )

    def _update_status_sync(self, table: str, message_id: str, status: str):
        """Synchronous status update."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute(f'UPDATE {table} SET status = ? WHERE message_id = ?', (status, message_id))
        conn.commit()
        conn.close()

    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message (blocks until available)."""
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> str:
        """Publish a response from the agent to channels with persistence."""
        import uuid
        message_id = str(uuid.uuid4())

        await self._persist_outbound(message_id, msg)

        await self.outbound.put(msg)
        logger.debug(f"Bus outbound: {msg.target_channel}:{msg.target_id} - {msg.content[:50]}...")

        return message_id

    async def _persist_outbound(self, message_id: str, msg: OutboundMessage):
        """Persist outbound message to database."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._persist_outbound_sync,
            message_id,
            msg
        )

    def _persist_outbound_sync(self, message_id: str, msg: OutboundMessage):
        """Synchronous persistence of outbound message."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO outbound_messages
                (message_id, target_channel, target_id, content, files, reply_to, metadata, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_id,
                msg.target_channel,
                msg.target_id,
                msg.content,
                json.dumps(msg.files),
                msg.reply_to,
                json.dumps(msg.metadata),
                'pending'
            ))
            conn.commit()
        except sqlite3.IntegrityError:
            pass
        finally:
            conn.close()

    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message (blocks until available)."""
        return await self.outbound.get()

    async def ack_outbound(self, message_id: str):
        """Acknowledge successful delivery of an outbound message."""
        await self._update_outbound_status(message_id, 'delivered')

    async def _update_outbound_status(self, message_id: str, status: str):
        """Update outbound message status."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._update_status_sync,
            'outbound_messages',
            message_id,
            status
        )

    async def move_to_dead_letter(self, message_type: str, message_data: dict, error: str):
        """Move a failed message to the dead letter queue."""
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._move_to_dead_letter_sync,
            message_type,
            message_data,
            error
        )

    def _move_to_dead_letter_sync(self, message_type: str, message_data: dict, error: str):
        """Synchronous dead letter queue insertion."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO dead_letter_queue (message_type, message_data, error_message)
            VALUES (?, ?, ?)
        ''', (message_type, json.dumps(message_data), error))

        conn.commit()
        conn.close()

    async def recover_pending_messages(self) -> tuple[list[InboundMessage], list[OutboundMessage]]:
        """Recover pending messages after restart."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._recover_pending_sync)

    def _recover_pending_sync(self) -> tuple[list[InboundMessage], list[OutboundMessage]]:
        """Synchronous recovery of pending messages."""
        from datetime import datetime

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM inbound_messages WHERE status = ?', ('pending',))
        inbound_rows = cursor.fetchall()

        cursor.execute('SELECT * FROM outbound_messages WHERE status = ?', ('pending',))
        outbound_rows = cursor.fetchall()

        conn.close()

        inbound_messages = []
        for row in inbound_rows:
            inbound_messages.append(InboundMessage(
                channel=row[2],
                sender_id=row[3],
                chat_id=row[4],
                content=row[5],
                media=json.loads(row[6]) if row[6] else [],
                metadata=json.loads(row[7]) if row[7] else {},
                timestamp=datetime.fromisoformat(row[8])
            ))

        outbound_messages = []
        for row in outbound_rows:
            outbound_messages.append(OutboundMessage(
                target_channel=row[2],
                target_id=row[3],
                content=row[4],
                files=json.loads(row[5]) if row[5] else [],
                reply_to=row[6],
                metadata=json.loads(row[7]) if row[7] else {}
            ))

        return inbound_messages, outbound_messages

    async def get_queue_sizes(self) -> dict:
        """Get current queue sizes for monitoring."""
        return {
            "inbound_queue": self.inbound.qsize(),
            "outbound_queue": self.outbound.qsize(),
            "pending_acks": len(self._pending_acks),
        }
