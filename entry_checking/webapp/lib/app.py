"""Flask app factory and console-script entry point for the entry-checker web UI.

Usage:
    entry-checker-web

    (or via -m: python -m entry_checking.webapp.lib.app)
"""

import os
import pathlib

from flask import Flask

from entry_checking.webapp.lib import routes

# webapp/ - templates/static live here, one level up from lib/.
_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent.parent


def create_app() -> Flask:
    """Build and configure the entry-checker Flask app."""
    app = Flask(
        "entry_checking.webapp",
        template_folder=str(_PACKAGE_ROOT / "templates"),
        static_folder=str(_PACKAGE_ROOT / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB
    app.register_blueprint(routes.bp)
    return app


def main() -> None:
    """Run the entry-checker web UI locally."""
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")


if __name__ == "__main__":
    main()
