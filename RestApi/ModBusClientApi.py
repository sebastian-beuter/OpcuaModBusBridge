import logging

from flask import Blueprint, Flask, current_app, jsonify, request

from ModBus.ModBusClient import ModBusClientManager


logger = logging.getLogger(__name__)
modbus_client_api = Blueprint("modbus_client_api", __name__)


@modbus_client_api.get("/connections")
def get_connections():
    clients: ModBusClientManager = current_app.config["MODBUS_CLIENTS"]
    return jsonify({"connections": clients.connected_ips()})


@modbus_client_api.post("/connections")
def connect_modbus_slave():
    clients: ModBusClientManager = current_app.config["MODBUS_CLIENTS"]
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or not isinstance(data.get("ip_address"), str):
        return jsonify({"error": 'JSON body must contain a string "ip_address"'}), 400

    ip_address = data["ip_address"]
    try:
        connected_now = clients.connect(ip_address)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except (ConnectionError, OSError):
        logger.exception("Could not connect to Modbus slave at %s", ip_address)
        return jsonify({"error": f"Could not connect to Modbus slave at {ip_address}:502"}), 502

    return (
        jsonify(
            {
                "ip_address": ip_address,
                "status": "connected" if connected_now else "already_connected",
            }
        ),
        201 if connected_now else 200,
    )


@modbus_client_api.delete("/connections/<ip_address>")
def disconnect_modbus_slave(ip_address: str):
    clients: ModBusClientManager = current_app.config["MODBUS_CLIENTS"]
    try:
        disconnected = clients.disconnect(ip_address)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    if not disconnected:
        return jsonify({"error": f"No connection exists for {ip_address}"}), 404

    return jsonify({"ip_address": ip_address, "status": "disconnected"})


def register_routes(app: Flask, clients: ModBusClientManager) -> None:
    app.config["MODBUS_CLIENTS"] = clients
    app.register_blueprint(modbus_client_api)