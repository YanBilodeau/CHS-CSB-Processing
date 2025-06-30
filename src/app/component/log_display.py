"""Log Display Component for displaying log output in a web UI."""

from typing import Protocol

from nicegui import ui


class LogHandlerProtocol(Protocol):
    def get_logs(self) -> list[str]:
        """Get all available logs."""
        ...

    def clear_logs(self) -> None:
        """Clear all logs."""
        ...


class LogDisplay:
    """Component for displaying log output."""

    def __init__(self, log_handler: LogHandlerProtocol) -> None:
        self.log_handler = log_handler
        self.container = None
        self.output = None
        self.visible = False
        self.toggle_button = None

    def create(self) -> ui.column:
        """Create the log display component."""
        # Log section header with toggle button
        with ui.row().classes("w-full justify-between items-center mt-4"):
            ui.label("Log Output").classes("text-lg font-bold")

            with ui.row().classes("gap-2"):
                ui.button(
                    "Clear logs", on_click=self.clear_logs, icon="clear_all"
                ).props("size=sm color=secondary outline")

                self.toggle_button = ui.button(
                    "Show logs", on_click=self.toggle_visibility, icon="visibility"
                ).props("size=sm color=primary outline")

        # Log container (initially hidden)
        self.container = ui.column().classes("w-full mt-2")
        with self.container:
            with ui.column().classes("w-full"):
                with ui.scroll_area().classes(
                    "w-full h-96 bg-gray-900 text-green-400 font-mono text-xs"
                ):
                    self.output = ui.column().classes("w-full p-2")

        self.container.visible = False

        # Start log update timer
        ui.timer(1.0, self.update_logs)

        return self.container

    def toggle_visibility(self) -> None:
        """Toggle log visibility."""
        if self.visible:
            self.hide()
        else:
            self.show()

    def show(self) -> None:
        """Show the log display if it's hidden."""
        if not self.visible:
            self.visible = True
            self.container.visible = True
            self.toggle_button.text = "Hide logs"
            self.toggle_button.icon = "visibility_off"
            self.update_logs()

    def hide(self) -> None:
        """Hide the log display if it's visible."""
        if self.visible:
            self.visible = False
            self.container.visible = False
            self.toggle_button.text = "Show logs"
            self.toggle_button.icon = "visibility"

    def clear_logs(self) -> None:
        """Clear all logs."""
        self.log_handler.clear_logs()

        if self.output:
            self.output.clear()

        ui.notification("Logs cleared", type="info")

    def update_logs(self) -> None:
        """Update log display with new log entries."""
        if not self.visible or not self.output:
            return

        new_logs: list[str] = self.log_handler.get_logs()

        if new_logs:
            with self.output:
                for log_message in new_logs:
                    color_class = self._get_log_color(log_message)
                    ui.label(log_message).classes(
                        f"{color_class} whitespace-pre-wrap break-all"
                    )

            # Auto-scroll to bottom
            ui.run_javascript(
                """
                const scrollArea = document.querySelector('.q-scrollarea__container');
                if (scrollArea) {
                    scrollArea.scrollTop = scrollArea.scrollHeight;
                }
            """
            )

    @staticmethod
    def _get_log_color(log_message: str) -> str:
        """Get color class based on log level."""
        if "ERROR" in log_message:
            return "text-red-400"
        elif "WARNING" in log_message:
            return "text-yellow-400"
        elif "INFO" in log_message:
            return "text-blue-400"
        elif "DEBUG" in log_message:
            return "text-gray-400"
        else:
            return "text-green-400"
