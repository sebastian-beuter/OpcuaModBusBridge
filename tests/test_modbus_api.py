import unittest
from unittest.mock import Mock, patch

import main
from ModBus.ModBusClient import ModBusClientManager


class ModbusApiTests(unittest.TestCase):
    def setUp(self):
        self.manager = ModBusClientManager()
        main.app.config["MODBUS_CLIENTS"] = self.manager

        self.client = Mock()
        self.client.connect.return_value = True
        client_patch = patch(
            "ModBus.ModBusClient.ModbusTcpClient", return_value=self.client
        )
        self.client_factory = client_patch.start()
        self.addCleanup(client_patch.stop)
        self.api = main.app.test_client()

    def test_connect_list_duplicate_and_disconnect(self):
        response = self.api.post(
            "/connections", json={"ip_address": "192.168.86.50"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["status"], "connected")
        self.client_factory.assert_called_once_with("192.168.86.50", port=502)

        response = self.api.post(
            "/connections", json={"ip_address": "192.168.86.50"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["status"], "already_connected")
        self.assertEqual(
            self.api.get("/connections").json,
            {"connections": ["192.168.86.50"]},
        )

        response = self.api.delete("/connections/192.168.86.50")
        self.assertEqual(response.status_code, 200)
        self.client.close.assert_called_once()
        self.assertEqual(self.api.get("/connections").json, {"connections": []})
        self.assertEqual(
            self.api.delete("/connections/192.168.86.50").status_code, 404
        )

    def test_invalid_request_and_ip_address(self):
        self.assertEqual(
            self.api.post("/connections", json={}).status_code, 400
        )
        self.assertEqual(
            self.api.post(
                "/connections", json={"ip_address": "not-an-ip"}
            ).status_code,
            400,
        )
        self.client_factory.assert_not_called()

    def test_unreachable_slave_returns_bad_gateway(self):
        self.client.connect.return_value = False

        with self.assertLogs("RestApi.ModBusClientApi", level="ERROR"):
            response = self.api.post(
                "/connections", json={"ip_address": "192.168.86.51"}
            )

        self.assertEqual(response.status_code, 502)
        self.client.close.assert_called_once()
        self.assertEqual(self.manager.connected_ips(), [])

    def test_measurement_returns_requested_registers(self):
        self.client.read_holding_registers.return_value = Mock(
            isError=Mock(return_value=False),
            registers=[123, 456],
        )
        self.manager.connect("192.168.86.50")

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 10, "count": 2},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json,
            {
                "ip_address": "192.168.86.50",
                "address": 10,
                "count": 2,
                "device_id": 1,
                "value": [123, 456],
                "decoded_values": {},
            },
        )
        self.client.read_holding_registers.assert_called_once_with(
            address=10,
            count=2,
            device_id=1,
        )

    def test_measurement_rejects_bad_register_parameters(self):
        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 65535, "count": 2},
        )
        self.assertEqual(response.status_code, 400)
        self.client.read_holding_registers.assert_not_called()

        response = self.api.post(
            "/measurements/192.168.86.50",
            json={"address": 10, "count": 1},
        )
        self.assertEqual(response.status_code, 404)

    def test_modbus_read_error_returns_bad_gateway(self):
        response_object = Mock()
        response_object.isError.return_value = True
        response_object.__str__ = Mock(return_value="Illegal data address")
        self.client.read_holding_registers.return_value = response_object
        self.manager.connect("192.168.86.50")

        with self.assertLogs("RestApi.MeasurementTasksApi", level="ERROR"):
            response = self.api.post(
                "/measurements/192.168.86.50",
                json={"address": 10, "count": 1},
            )

        self.assertEqual(response.status_code, 502)
        self.assertIn("Illegal data address", response.json["error"])


if __name__ == "__main__":
    unittest.main()
