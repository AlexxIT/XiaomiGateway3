# Xiaomi Gateway 3 integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://money.yandex.ru/to/41001428278477)

Control Zigbee devices from Home Assistant with **Xiaomi Gateway 3 (ZNDMWG03LM)** on original firmware.

Gateway support **Zigbee 3**, **Bluetooth Mesh** and **HomeKit**.

This method does not change the device firmware. Gateway continues to work with Mi Home and HomeKit.

Thanks to **Serrj** for [instruction how to enable Telnet](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) on this device.

# Supported Devices

Currently supported and tested several Xiaomi and Aqara Zibee devices officially supported by the Gateway:

> Aqara Cube, Aqara Double Wall Button, Aqara Motion Sensor, Aqara Opple Six Button, Aqara Relay, Aqara Vibration Sensor, Aqara Water Leak Sensor, IKEA Bulb E14, Xiaomi Button, Xiaomi Plug, Xiaomi TH Sensor

Plans to support officially supported Bluetooth devices.

Plans to support for Zigbee devices from other manufacturers. May be support for [ZHA](https://www.home-assistant.io/integrations/zha/).

# Install

[![Xiaomi Gateway 3 control from Home Assistant](https://img.youtube.com/vi/CQVSFISC9CE/mqdefault.jpg)](https://www.youtube.com/watch?v=CQVSFISC9CE)

You can install component with HACS custom repo ([example](https://github.com/AlexxIT/SonoffLAN#install-with-hacs)): `AlexxIT/XiaomiGateway3`.

Or manually copy `xiaomi_gateway3` folder from latest release to `custom_components` folder in your config folder.

# Config

With GUI. Configuration > Integration > Xiaomi Gateway 3. And enter Gateway **IP address** and **Mi Home token**.

You need [obtain Mi Home token](https://github.com/Maxmudjon/com.xiaomi-miio/blob/master/docs/obtain_token.md). I am using the [method with Mi Home v5.4.54](https://github.com/Maxmudjon/com.xiaomi-miio/blob/master/docs/obtain_token.md#non-rooted-android-phones) for non-rooted Android. If you don't have an Android - you can install the [emulator on Windows](https://www.bignox.com/).

# How it works

The component enables **Telnet** on Gateway via [Miio protocol](https://github.com/rytilahti/python-miio). Only this Gateway supports this command. Do not try to execute it on other Xiaomi/Aqara Gateways.

The component starts the **MQTT Server** on the public port of the Gateway. All the logic in the Gateway runs on top of the built-in MQTT Server. By default, access to it is closed from the outside.

**ATTENTION:** Telnet and MQTT work without a password! Do not use this method on public networks.

After rebooting the device, all changes will be reset. The component will launch Telnet and public MQTT every time it detects that they are disabled.