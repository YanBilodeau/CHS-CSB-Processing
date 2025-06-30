"""Network helper functions for finding a free port."""

import socket


def find_free_port(start_port: int = 8080, max_attempts: int = 100) -> int:
    """Find a free port starting from start_port."""
    for port in range(start_port, start_port + max_attempts):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", port))

                return port

        except OSError:
            continue

    raise RuntimeError(
        f"No free port found in range {start_port}-{start_port + max_attempts}"
    )
