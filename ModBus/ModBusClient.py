import ipaddress
import logging
from threading import RLock

from pymodbus.client import ModbusTcpClient


logger = logging.getLogger(__name__)


class ModbusReadError(Exception):
    pass


class ModBusClientManager:
    def __init__(self, port: int = 502):
        self.port = port
        self._clients: dict[str, ModbusTcpClient] = {}
        self._lock = RLock()

    @staticmethod
    def _normalize_ip_address(ip_address: str) -> str:
        if not isinstance(ip_address, str) or not ip_address.strip():
            raise ValueError("A valid IP address is required")

        try:
            return str(ipaddress.ip_address(ip_address.strip()))
        except ValueError as error:
            raise ValueError(f"Invalid IP address: {ip_address}") from error

    def connect(self, ip_address: str) -> bool:
        address = self._normalize_ip_address(ip_address)

        with self._lock:
            if address in self._clients:
                return False

            client = ModbusTcpClient(address, port=self.port)
            try:
                connected = client.connect()
            except OSError:
                client.close()
                raise

            if not connected:
                client.close()
                raise ConnectionError(
                    f"Could not connect to Modbus slave at {address}:{self.port}"
                )

            self._clients[address] = client
            return True

    def disconnect(self, ip_address: str) -> bool:
        address = self._normalize_ip_address(ip_address)

        with self._lock:
            client = self._clients.pop(address, None)
            if client is None:
                return False

            client.close()
            return True

    def connected_ips(self) -> list[str]:
        with self._lock:
            return sorted(self._clients)

    def read_holding_registers(
        self,
        ip_address: str,
        address: int,
        count: int,
        device_id: int = 1,
    ) -> list[int]:
        ip_address = self._normalize_ip_address(ip_address)
        if not 0 <= address <= 65535:
            raise ValueError("Register address must be between 0 and 65535")
        if not 1 <= count <= 125 or address + count > 65536:
            raise ValueError("Register count must be between 1 and 125")
        if not 1 <= device_id <= 247:
            raise ValueError("Device ID must be between 1 and 247")

        with self._lock:
            client = self._clients.get(ip_address)
            if client is None:
                raise LookupError(f"No connection exists for {ip_address}")

            result = client.read_holding_registers(
                address=address,
                count=count,
                device_id=device_id,
            )
            if result.isError():
                raise ModbusReadError(str(result))

            return list(result.registers)

    def close_all(self) -> None:
        with self._lock:
            clients = list(self._clients.items())
            self._clients.clear()

        for address, client in clients:
            try:
                client.close()
            except Exception:
                logger.exception("Could not close Modbus connection to %s", address)
