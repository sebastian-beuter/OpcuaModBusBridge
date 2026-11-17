import unittest
from unittest.mock import Mock

from flask import Flask

from ModBus.ModBusClient import ModbusReadError
from RestApi.MeasurementTasksApi import register_routes


class MeasurementTasksApiTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.clients = Mock()
        self.app.config["MODBUS_CLIENTS"] = self.clients
        register_routes(self.app)
        self.api = self.app.test_client()

    def test_measurement_returns_requested_registers(self):
        self.clients.read_holding_registers.return_value = [123, 456]

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 10, "count": 2, "device_id": 7},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "ip_address": "192.168.86.50",
                "address": 10,
                "count": 2,
                "device_id": 7,
                "value": [123, 456],
                "decoded_values": {},
            },
        )
        self.clients.read_holding_registers.assert_called_once_with(
            "192.168.86.50",
            address=10,
            count=2,
            device_id=7,
        )

    def test_measurement_uses_default_device_id(self):
        self.clients.read_holding_registers.return_value = [321]

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 3, "count": 1},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["device_id"], 1)
        self.assertEqual(response.json["value"], [321])
        self.assertEqual(response.json["decoded_values"], {})
        self.clients.read_holding_registers.assert_called_once_with(
            "192.168.86.50",
            address=3,
            count=1,
            device_id=1,
        )

    def test_measurement_decodes_arduino_voltage_and_current_registers(self):
        self.clients.read_holding_registers.return_value = [
            0x4140,
            0x0000,
            0x3FC0,
            0x0000,
        ]

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 0, "count": 4},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["value"], [0x4140, 0, 0x3FC0, 0])
        self.assertEqual(
            response.json["decoded_values"],
            {"voltage": 12.0, "current": 1.5},
        )

    def test_measurement_decodes_voltage_when_only_voltage_registers_are_read(self):
        self.clients.read_holding_registers.return_value = [0x4140, 0x0000]

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 0, "count": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["decoded_values"], {"voltage": 12.0})

    def test_missing_or_non_integer_parameters_return_bad_request(self):
        responses = [
            self.api.post(
                "/measurements/192.168.86.50",
                json={"address": 1},
            ),
            self.api.post(
                "/measurements/192.168.86.50",
                json={"address": "1", "count": 1},
            ),
            self.api.post(
                "/measurements/192.168.86.50",
                json={"address": 1, "count": True},
            ),
            self.api.post("/measurements/192.168.86.50", json=[]),
        ]

        self.assertEqual([response.status_code for response in responses], [400] * 4)
        self.clients.read_holding_registers.assert_not_called()

    def test_invalid_register_range_returns_bad_request(self):
        self.clients.read_holding_registers.side_effect = ValueError(
            "Register count must be between 1 and 125"
        )

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 65535, "count": 2},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Register count", response.json["error"])

    def test_unconnected_slave_returns_not_found(self):
        self.clients.read_holding_registers.side_effect = LookupError(
            "No connection exists for 192.168.86.50"
        )

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 0, "count": 1},
        )

        self.assertEqual(response.status_code, 404)

    def test_modbus_read_error_returns_bad_gateway(self):
        self.clients.read_holding_registers.side_effect = ModbusReadError(
            "Illegal data address"
        )

        with self.assertLogs("RestApi.MeasurementTasksApi", level="ERROR"):
            response = self.api.post(
                "/measurements/192.168.86.50",
                json={"address": 0, "count": 1},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("Illegal data address", response.json["error"])


if __name__ == "__main__":
    unittest.main()
