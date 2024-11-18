import warnings

class WarningCapture:
    def __init__(self):
        self.captured_warnings = []

    def __enter__(self):
        self._original_showwarning = warnings.showwarning
        warnings.showwarning = self._capture_warning

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        warnings.showwarning = self._original_showwarning

    def _capture_warning(
        self, message, category, filename, lineno, file=None, line=None
    ):
        self.captured_warnings.append(str(message))
