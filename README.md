# Xiaomi Gateway 3 integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://money.yandex.ru/to/41001428278477)

Control Zigbee devices from Home Assistant with **Xiaomi Gateway 3 (ZNDMWG03LM)** on original firmware.

Gateway support **Zigbee 3**, **Bluetooth Mesh** and **HomeKit**.

This method does not change the device firmware. Gateway continues to work with Mi Home and HomeKit.

Thanks to **Serrj** for [instruction how to enable Telnet](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) on this device.

# Supported Zigbee Devices

Tested Devices:
- Aqara Cube (MFKZQ01LM)
- Aqara Double Wall Button (WXKG02LM)
- Aqara Motion Sensor (RTCGQ11LM)
- Aqara Opple Six Button (WXCJKG13LM)
- Aqara Relay (LLKZMK11LM)
- Aqara Vibration Sensor (DJT11LM)
- Aqara Water Leak Sensor (SJCGQ11LM)
- IKEA Bulb E14
- Xiaomi Button (WXKG01LM)
- Xiaomi Door Sensor (MCCGQ01LM)
- Xiaomi Light Sensor (GZCGQ01LM)
- Xiaomi Plug (ZNCZ02LM)
- Xiaomi TH Sensor (WSDCGQ01LM)

Currently supported, but not tested other Xiaomi and Aqara Zibee devices officially supported by the Gateway. Check list [here](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/utils.py#L9).

Plans to support for Zigbee devices from other manufacturers. May be support for [ZHA](https://www.home-assistant.io/integrations/zha/).

# Supported BLE Devices

Tested Devices:
- Xiaomi TH Sensor (LYWSDCGQ/01ZM)

Currently supported, but not tested, other Xiaomi BLE devices officially supported by the Gateway with these attributes:

> temperature, humidity, motion, illuminance, moisture, conductivity, formaldehyde, mosquitto, battery

BLE devices and their attributes do not appear immediately! And don't save their data across HA reboots! Their data is updated only when the device itself sends them. Temperature, humidity and battery may refresh at different times.

# Install

HOWTO video:

[![Xiaomi Gateway 3 control from Home Assistant](https://img.youtube.com/vi/CQVSFISC9CE/mqdefault.jpg)](https://www.youtube.com/watch?v=CQVSFISC9CE)

You can install component with HACS custom repo ([example](https://github.com/AlexxIT/SonoffLAN#install-with-hacs)): `AlexxIT/XiaomiGateway3`.

Or manually copy `xiaomi_gateway3` folder from latest release to `custom_components` folder in your config folder.

# Config

With GUI. Configuration > Integration > Xiaomi Gateway 3. And enter Gateway **IP address** and **Mi Home token**.

You need [obtain Mi Home token](https://github.com/Maxmudjon/com.xiaomi-miio/blob/master/docs/obtain_token.md). I am using the [method with Mi Home v5.4.54](https://github.com/Maxmudjon/com.xiaomi-miio/blob/master/docs/obtain_token.md#non-rooted-android-phones) for non-rooted Android. If you don't have an Android - you can install the [emulator on Windows](https://www.bignox.com/).

# Advanced config

Support custom occupancy timeout for motion sensor. Default 90 seconds.

```yaml
xiaomi_gateway3:
  devices:
    '0x158d00044c5dff':
      occupancy_timeout: 15  # (optional) default 90 seconds
```

# How it works

The component enables **Telnet** on Gateway via [Miio protocol](https://github.com/rytilahti/python-miio). Only this Gateway supports this command. Do not try to execute it on other Xiaomi/Aqara Gateways.

The component starts the **MQTT Server** on the public port of the Gateway. All the logic in the Gateway runs on top of the built-in MQTT Server. By default, access to it is closed from the outside.

**ATTENTION:** Telnet and MQTT work without a password! Do not use this method on public networks.

After rebooting the device, all changes will be reset. The component will launch Telnet and public MQTT every time it detects that they are disabled.

# Debug mode

Component support debug mode. Shows only component logs. The link to the logs is always random.

Demo video of my other component, but the idea is the same:

[![Control Sonoff Devices with eWeLink firmware over LAN from Home Assistant](https://img.youtube.com/vi/Lt5fT4N5Pm8/mqdefault.jpg)](https://www.youtube.com/watch?v=Lt5fT4N5Pm8)

With `debug: bluetooth` or debug `debug: mqtt` opntion you will get advanced log for raw BLE and MQTT data.

With `debug: true` option you will get usual component logs.

```yaml
xiaomi_gateway3:
  debug: true  # you will get HA notification with a link to the logs page
```

You can filter data in the logs and enable auto refresh (in seconds).

```
http://192.168.1.123:8123/c4e99cfc-0c83-4a39-b7f0-278b0e719bd1?q=ble_event&r=2
```
