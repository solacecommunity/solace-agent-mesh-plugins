import logging
import threading
from pathlib import Path
from typing import Optional
from flask import Flask, send_from_directory, render_template_string

logger = logging.getLogger(__name__)

# Global web server instance
_web_server_instance = None
_server_thread = None


class ArtifactWebServer:
    """Flask-based web server for hosting artifacts."""

    def __init__(self, host_directory: Path, port: int = 8080, host: str = "127.0.0.1"):
        """
        Initialize the artifact web server.

        Args:
            host_directory: Directory containing files to serve
            port: Port to bind to (default: 8080)
            host: Host to bind to (default: 127.0.0.1)
        """
        self.host_directory = host_directory
        self.port = port
        self.host = host
        self.app = Flask(__name__)
        self.server_thread = None

        # Ensure host directory exists
        self.host_directory.mkdir(parents=True, exist_ok=True)

        # Setup routes
        self._setup_routes()

        logger.info(f"[ArtifactWebServer] Initialized with directory: {host_directory}, port: {port}")

    def _setup_routes(self):
        """Setup Flask routes."""

        @self.app.route('/')
        def index():
            """Directory listing page."""
            files = []
            if self.host_directory.exists():
                for file_path in sorted(self.host_directory.iterdir()):
                    if file_path.is_file():
                        size_bytes = file_path.stat().st_size
                        size_mb = size_bytes / (1024 * 1024)
                        files.append({
                            'name': file_path.name,
                            'size_bytes': size_bytes,
                            'size_display': f"{size_mb:.2f} MB" if size_mb >= 1 else f"{size_bytes / 1024:.2f} KB"
                        })

            html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Hosted Artifacts</title>
                <style>
                    body {
                        font-family: Arial, sans-serif;
                        max-width: 1200px;
                        margin: 40px auto;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    h1 {
                        color: #333;
                        border-bottom: 2px solid #4CAF50;
                        padding-bottom: 10px;
                    }
                    .file-list {
                        background-color: white;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        padding: 20px;
                    }
                    table {
                        width: 100%;
                        border-collapse: collapse;
                    }
                    th {
                        background-color: #4CAF50;
                        color: white;
                        padding: 12px;
                        text-align: left;
                    }
                    td {
                        padding: 12px;
                        border-bottom: 1px solid #ddd;
                    }
                    tr:hover {
                        background-color: #f5f5f5;
                    }
                    a {
                        color: #4CAF50;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    .empty {
                        text-align: center;
                        color: #666;
                        padding: 40px;
                    }
                </style>
            </head>
            <body>
                <h1>Hosted Artifacts</h1>
                <div class="file-list">
                    {% if files %}
                    <table>
                        <thead>
                            <tr>
                                <th>Filename</th>
                                <th>Size</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for file in files %}
                            <tr>
                                <td><a href="/{{ file.name }}">{{ file.name }}</a></td>
                                <td>{{ file.size_display }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                    {% else %}
                    <div class="empty">No artifacts hosted yet.</div>
                    {% endif %}
                </div>
            </body>
            </html>
            """
            return render_template_string(html, files=files)

        @self.app.route('/<path:filename>')
        def serve_file(filename):
            """Serve individual files."""
            return send_from_directory(self.host_directory, filename)

    def start(self):
        """Start the web server in a background thread."""
        if self.server_thread and self.server_thread.is_alive():
            logger.warning("[ArtifactWebServer] Server is already running")
            return

        def run_server():
            logger.info(f"[ArtifactWebServer] Starting Flask server on {self.host}:{self.port}")
            # Disable Flask's default logging to avoid clutter
            import logging as flask_logging
            log = flask_logging.getLogger('werkzeug')
            log.setLevel(flask_logging.ERROR)

            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        logger.info(f"[ArtifactWebServer] Server started on http://{self.host}:{self.port}")

    def stop(self):
        """Stop the web server (note: Flask doesn't have built-in graceful shutdown)."""
        # Flask's development server doesn't support graceful shutdown
        # In production, you'd use a proper WSGI server like gunicorn
        logger.info("[ArtifactWebServer] Server shutdown requested (daemon thread will stop with process)")

    def get_url(self, filename: str, base_url: Optional[str] = None) -> str:
        """
        Get the URL for accessing a hosted file.

        Args:
            filename: Name of the hosted file
            base_url: Optional custom base URL (e.g., for proxy/firewall scenarios)

        Returns:
            Full URL to access the file
        """
        if base_url:
            # Use custom base URL (for firewall/proxy scenarios)
            return f"{base_url.rstrip('/')}/{filename}"
        else:
            # Use default localhost URL
            return f"http://{self.host}:{self.port}/{filename}"


def get_web_server() -> Optional[ArtifactWebServer]:
    """Get the global web server instance."""
    return _web_server_instance


def set_web_server(server: ArtifactWebServer):
    """Set the global web server instance."""
    global _web_server_instance
    _web_server_instance = server
