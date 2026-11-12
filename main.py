import atexit
import logging

from flask import Flask

from ModBus.ModBusClient import ModBusClientManager
from RestApi.MeasurementTasksApi import register_routes as register_measurement_routes
from RestApi.ModBusClientApi import register_routes
from RestApi.SwaggerApi import register_swagger_ui


logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
modbus_clients = ModBusClientManager()
register_routes(app, modbus_clients)
register_measurement_routes(app)
register_swagger_ui(app)
atexit.register(modbus_clients.close_all)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001)
