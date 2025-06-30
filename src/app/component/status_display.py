"""Status display component for showing processing status in the UI."""

from nicegui import ui


class StatusDisplay:
    """Component for displaying processing status."""

    def __init__(self) -> None:
        self.label = None

    def create(self) -> ui.label:
        """Create the status display component."""
        self.label = ui.label("⏳ Ready to process files").classes(
            "text-gray-600 text-base p-2"
        )
        return self.label

    def set_status(self, text: str, status_type: str = "info") -> None:
        """Set the status with appropriate styling."""
        if not self.label:
            return

        self.label.text = text

        # Remove any existing status classes
        self.label.classes(remove="status-flashing")

        if status_type == "processing":
            self.label.style("color: #1976d2; font-weight: bold;")
            self.label.classes("status-flashing")
        elif status_type == "success":
            self.label.style("color: #388e3c; font-weight: bold;")
        elif status_type == "error":
            self.label.style("color: #d32f2f; font-weight: bold;")
        else:  # info
            self.label.style("color: #666; font-weight: normal;")
