"""Flask app factory and console-script entry point for the points-updater web UI.

Usage:
    points-updater-web

    (or via -m: python -m points_updating.lib.webapp.app)
"""

import os
import pathlib

from flask import Flask

from points_updating.lib.webapp import routes

# templates/ and static/ are siblings of this file within webapp/.
_PACKAGE_ROOT = pathlib.Path(__file__).resolve().parent


def create_app() -> Flask:
    """Build and configure the points-updater Flask app."""
    app = Flask(
        "points_updating.lib.webapp",
        template_folder=str(_PACKAGE_ROOT / "templates"),
        static_folder=str(_PACKAGE_ROOT / "static"),
    )
    app.register_blueprint(routes.bp)
    return app


def main() -> None:
    """Run the points-updater web UI locally."""
    create_app().run(debug=os.environ.get("FLASK_DEBUG") == "1")


if __name__ == "__main__":
    main()
