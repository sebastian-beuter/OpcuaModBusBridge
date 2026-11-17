This application is intended to bridge an OPC UA server interface over Wi-Fi and
a Modbus interface over Ethernet on a Raspberry Pi. The Raspberry Pi's Wi-Fi IP
address is currently configured as `192.168.86.100`.

## Modbus connection API

The Flask API listens on port `5001` and uses Modbus TCP port `502` for slave
connections. Start it with:

```sh
pip install -r requirements.txt
python main.py
```

The API binds to all network interfaces. Connections are held in memory and are
closed when the application exits. The API has no authentication; restrict port
`5001` to trusted clients and networks.

The interactive, locally served Swagger UI is available at
`http://127.0.0.1:5001/offline/docs`. It can execute the API endpoints from the
browser. Its OpenAPI document is served from `/openapi.json`; the UI assets are
bundled with the application and do not require an internet connection.

### Connect to a slave

`POST /connections` with a JSON body:

```json
{"ip_address": "192.168.86.50"}
```

Returns `201` for a new connection, `200` if that address is already connected,
`400` for an invalid IP address or request body, and `502` if the slave cannot
be reached.

### List connections

`GET /connections` returns the connected slave IP addresses:

```json
{"connections": ["192.168.86.50"]}
```

### Disconnect from a slave

`DELETE /connections/192.168.86.50` closes the connection for that IP address.
Returns `404` if no connection is registered for the address.

## Trigger a measurement

`POST /measurements/192.168.86.50` reads holding registers from an already
connected slave. Provide the starting register address and number of registers
in the JSON body; `device_id` is optional and defaults to `1`:

```json
{"address": 0, "count": 2}
```

The response body contains the raw register values in `value`:

```json
{
  "ip_address": "192.168.86.50",
  "address": 0,
  "count": 2,
  "device_id": 1,
  "value": [123, 456]
}
```

The Arduino example stores voltage in registers `0`-`1` and current in
registers `2`-`3`, with each IEEE 754 float sent high-word first. To read both
measurements, request `{"address": 0, "count": 4}`. The response retains the
raw register list in `value` and adds decoded float values in `decoded_values`:

```json
{
  "address": 0,
  "count": 4,
  "value": [16704, 0, 16320, 0],
  "decoded_values": {
    "voltage": 12.0,
    "current": 1.5
  }
}
```

The endpoint returns `400` for invalid parameters, `404` if the slave is not
connected, and `502` if the Modbus read fails.
