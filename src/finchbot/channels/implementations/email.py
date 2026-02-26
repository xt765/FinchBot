import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from loguru import logger

from finchbot.channels.base import BaseChannel
from finchbot.channels.schema import OutboundMessage


class EmailChannel(BaseChannel):
    """Email Channel - simplified like nanobot."""

    name = "email"

    def __init__(self, config, bus):
        super().__init__(config, bus)
        cfg = config.get("email", {})
        self.smtp_host = cfg.get("smtp_host")
        self.smtp_port = cfg.get("smtp_port", 587)
        self.smtp_user = cfg.get("smtp_user")
        self.smtp_password = cfg.get("smtp_password")
        self.from_address = cfg.get("from_address", self.smtp_user)
        self.use_tls = cfg.get("use_tls", True)

    async def start(self):
        if not self.smtp_host or not self.smtp_user:
            logger.warning("Email credentials not configured")
            return
        logger.info("Email channel ready")

    async def stop(self):
        logger.info("Email stopped")

    async def send(self, msg: OutboundMessage):
        if not self.smtp_host:
            return

        loop = asyncio.get_running_loop()

        def _send():
            message = MIMEMultipart("alternative")
            message["From"] = self.from_address
            message["To"] = msg.target_id
            message["Subject"] = msg.metadata.get("subject", "FinchBot") if msg.metadata else "FinchBot"

            message.attach(MIMEText(msg.content, "plain"))

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                if self.use_tls:
                    server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_address, msg.target_id, message.as_string())

        try:
            await loop.run_in_executor(None, _send)
            logger.debug(f"Email sent to {msg.target_id}")
        except Exception as e:
            logger.error(f"Email send error: {e}")

    @property
    def connection_count(self):
        return 1 if self.smtp_host else 0

    @property
    def status(self):
        return "running" if self.smtp_host else "stopped"
