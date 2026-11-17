import logging

from flask import Blueprint, Flask, current_app, jsonify, request
from pymodbus.exceptions import ModbusException

from ModBus.ModBusClient import ModBusClientManager, ModbusReadError


logger = logging.getLogger(__name__)
measurement_tasks_api = Blueprint("measurement_tasks_api", __name__)


@measurement_tasks_api.post("/measurements/<ip_address>")
def trigger_measurement(ip_address: str):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "JSON body must be an object"}), 400

    address = data.get("address")
    count = data.get("count")
    device_id = data.get("device_id", 1)
    if type(address) is not int or type(count) is not int or type(device_id) is not int:
        return jsonify(
            {"error": '"address", "count", and "device_id" must be integers'}
        ), 400

    clients: ModBusClientManager = current_app.config["MODBUS_CLIENTS"]
    try:
        values = clients.read_holding_registers(
            ip_address,
            address=address,
            count=count,
            device_id=device_id,
        )
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except LookupError as error:
        return jsonify({"error": str(error)}), 404
    except (ModbusReadError, ModbusException, OSError, ConnectionError) as error:
        logger.exception("Could not read Modbus registers from %s", ip_address)
        return jsonify({"error": f"Could not read registers from {ip_address}: {error}"}), 502

    decoded_values: dict[str, float] = {}
    request_end = address + count
    for name, first_register in (("voltage", 0), ("current", 2)):
        if address <= first_register and request_end >= first_register + 2:
            offset = first_register - address
            decoded_values[name] = ModBusClientManager.decode_float_registers(
                values[offset : offset + 2]
            )

    return jsonify(
        {
            "ip_address": ip_address,
            "address": address,
            "count": count,
            "device_id": device_id,
            "value": values,
            "decoded_values": decoded_values,
        }
    )


def register_routes(app: Flask) -> None:
    app.register_blueprint(measurement_tasks_api)