"""
Log handler module for capturing and displaying logs in the NiceGUI interface.
"""

from queue import Queue, Empty
from loguru import logger


class UILogHandler:
    """Custom log handler to capture logs for UI display."""

    FORMAT: str = "{time:YYYY-MM-DD HH:mm:ss} | {level:^8} | {message}"

    def __init__(self, level: str = "INFO") -> None:
        self.log_queue = Queue()
        self.max_logs: int = 100  # Keep only last 100 log entries
        self.level: str = level

    def write(self, message: str) -> None:
        """Write log message to queue."""
        if message.strip():
            self.log_queue.put(message.strip())

    def get_logs(self) -> list[str]:
        """Get all available logs from queue."""
        logs: list[str] = []

        try:
            while True:
                log = self.log_queue.get_nowait()
                logs.append(log)
                if len(logs) >= self.max_logs:
                    break

        except Empty:
            pass

        return logs

    def clear_logs(self) -> None:
        """Clear all logs from the queue."""
        with self.log_queue.mutex:
            self.log_queue.queue.clear()

    def setup_logger(self) -> None:
        """Setup custom log handler for UI display."""
        logger.add(
            sink=self.write,
            format=self.FORMAT,
            level=self.level,
        )

    def get_log_settings(self) -> dict:
        """Get log configuration for external loggers."""
        return dict(
            sink=self.write,
            format=self.FORMAT,
            level=self.level,
        )
