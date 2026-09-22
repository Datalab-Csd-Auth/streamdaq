# 📊 Compact vs Native Data Formats

In streaming systems (especially IoT and edge scenarios), two representation styles are common: **native** and **compact** formats.

## Native format

Native format stores each measurement as its own record.

```json title="Native format"
{"timestamp": 1640995200, "sensor_id": "env_001", "field": "temperature", "value": 23.5}
{"timestamp": 1640995200, "sensor_id": "env_001", "field": "humidity", "value": 65.2}
{"timestamp": 1640995200, "sensor_id": "env_001", "field": "pressure", "value": 1013.25}
```

**Strengths**

- Direct field-level access
- Broad compatibility with existing tools
- Flexible schema evolution

**Costs**

- Repeated metadata in each message
- Higher bandwidth and storage overhead

## Compact format

Compact format groups related measurements in one record.

```json title="Compact format"
{
  "timestamp": 1640995200,
  "sensor_id": "env_001",
  "fields": ["temperature", "humidity", "pressure"],
  "values": [23.5, 65.2, 1013.25]
}
```

**Strengths**

- Better transmission efficiency
- Lower metadata redundancy
- Better fit for constrained links/devices

**Costs**

- Additional unpacking/transformation effort
- More rigid producer/consumer schema coupling

## Choosing a format

| Scenario | Better fit |
| --- | --- |
| Rich tooling, easy debugging, dynamic schemas | **Native** |
| Bandwidth-constrained IoT, high-frequency telemetry | **Compact** |

!!! note "IoT reality"
    Compact formats are common in IoT because battery, bandwidth, and connectivity constraints reward smaller payloads.

## Summary

Choose the format that fits your infrastructure and operational constraints. Monitoring design should still preserve clear semantics for time, identity, and field meaning.
