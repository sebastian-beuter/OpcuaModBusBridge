from pathlib import Path

from flask import Flask, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint


_API_DIRECTORY = Path(__file__).resolve().parent
_SWAGGER_URL = "/offline/docs"
_OPENAPI_URL = "/openapi.json"


def register_swagger_ui(app: Flask) -> None:
    @app.get(_OPENAPI_URL)
    def openapi_specification():
        return send_from_directory(_API_DIRECTORY, "openapi.json")

    swagger_blueprint = get_swaggerui_blueprint(
        _SWAGGER_URL,
        _OPENAPI_URL,
        config={"app_name": "Modbus Bridge API"},
        blueprint_name="offline_swagger_ui",
    )
    app.register_blueprint(swagger_blueprint)
