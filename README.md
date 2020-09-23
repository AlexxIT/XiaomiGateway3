# Xiaomi Gateway 3 integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://money.yandex.ru/to/41001428278477)

Control Zigbee devices from Home Assistant with **Xiaomi Gateway 3 (ZNDMWG03LM)** on original firmware.

Gateway support **Zigbee 3**, **Bluetooth Mesh** and **HomeKit**.

This method does not change the device firmware. Gateway continues to work with Mi Home and HomeKit.

Thanks to **Serrj** for [instruction](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) how to enable Telnet on this device.

**Important:** This component does not work with:
 - Xiaomi Gateway 2 (DGNWG02LM, lumi.gateway.v3) - use [this](https://www.home-assistant.io/integrations/xiaomi_aqara/) component
 - Xiaomi Gateway EU (DGNWG05LM, lumi.gateway.mieu01)

# Supported Zigbee Devices

Tested Devices:
- Aqara Bulb (ZNLDP12LM)
- Aqara Button (WXKG11LM)
- Aqara Cube (MFKZQ01LM)
- Aqara Door Sensor (MCCGQ11LM)
- Aqara Double Wall Button (WXKG02LM)
- Aqara Motion Sensor (RTCGQ11LM)
- Aqara Opple Six Button (WXCJKG13LM)
- Aqara Relay (LLKZMK11LM)
- Aqara Socket (QBCZ11LM)
- Aqara Vibration Sensor (DJT11LM)
- Aqara Wall Double Switch (QBKG03LM)
- Aqara Water Leak Sensor (SJCGQ11LM)
- IKEA Bulb E14
- Xiaomi Button (WXKG01LM)
- Xiaomi Door Sensor (MCCGQ01LM)
- Xiaomi Light Sensor (GZCGQ01LM)
- Xiaomi Motion Sensor (RTCGQ01LM)
- Xiaomi Plug (ZNCZ02LM)
- Xiaomi Plug EU (ZNCZ04LM)
- Xiaomi TH Sensor (WSDCGQ01LM)

Currently supported, but not tested other Xiaomi and Aqara Zibee devices officially supported by the Gateway. Check list [here](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/utils.py).

Plans to support for Zigbee devices from other manufacturers. May be support for [ZHA](https://www.home-assistant.io/integrations/zha/).

# Supported BLE Devices

Demo video:

[![Xiaomi Rubik's Cube](https://img.youtube.com/vi/4D_vqvUre_0/mqdefault.jpg)](https://www.youtube.com/watch?v=4D_vqvUre_0)

Tested Devices:
- Aqara N100 Smart Door Lock
- Xiaomi Door Sensor 2 (MCCGQ02HL)
- Xiaomi Flower Monitor (HHCCJCY01)
- Xiaomi Loock Smart Lock
- Xiaomi Rubik's Cube (XMMF01JQD) - don't sends edge info, only direction!
- Xiaomi TH Sensor (LYWSD03MMC)
- Xiaomi TH Sensor (LYWSDCGQ/01ZM)
- Xiaomi TH Watch (LYWSD02MMC)


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

**Attention:** The component is under active development. Breaking changes may appear.

# Advanced config

Support custom occupancy timeout for motion sensor. Default 90 seconds.

```yaml
xiaomi_gateway3:
  devices:
    '0x158d00044c5dff':
      occupancy_timeout: 90  # (optional) default 90 seconds
```

# Handle Button Actions

[![Handling Zigbee buttons with Xiaomi Gateway 3 in Home Assistant](https://img.youtube.com/vi/a8hsNlTErac/mqdefault.jpg)](https://www.youtube.com/watch?v=a8hsNlTErac)

Buttons, vibration sensor, cube, locks and other - create an action entity. The entity changes its state for a split second and returns to an empty state. The attributes contain useful data, they are not cleared after the event is triggered.

```yaml
automation:
- alias: Turn off all lights
  trigger:
  - platform: state
    entity_id: sensor.0x158d0002fa99fd_action
    to: button_1_single
  action:
  - service: light.turn_off
    entity_id: all
  mode: single
```

# Handle BLE Locks

<img src="bluetooth_lock.png" width="810">

BLE locks have an action entity, just like buttons.

The state changes to `door`, `lock`, `fingerprint`,` armed` when an event occurs. Details of the event are in the entity attributes.

`action`: **fingerprint**
- `key_id` - Key ID in full hex format
- `action_id`: 0, `message`: Match successful
- `action_id`: 1, `message`: Match failed
- `action_id`: 2, `message`: Timeout
- `action_id`: 3, `message`: Low quality
- `action_id`: 4, `message`: Insufficient area
- `action_id`: 5, `message`: Skin is too dry
- `action_id`: 5, `message`: Skin is too wet

`action`: **door**
- `action_id`: 0, `message`: Door is open
- `action_id`: 1, `message`: Door is closed
- `action_id`: 2, `message`: Timeout is not closed
- `action_id`: 3, `message`: Knock on the door
- `action_id`: 4, `message`: Breaking the door
- `action_id`: 5, `message`: Door is stuck

`action`: **lock**
- `key_id` - Key ID in short decimal format
- `action_id`: 0, `message`: Unlock outside the door
- `action_id`: 1, `message`: Lock
- `action_id`: 2, `message`: Turn on anti-lock
- `action_id`: 3, `message`: Turn off anti-lock
- `action_id`: 4, `message`: Unlock inside the door
- `action_id`: 5, `message`: Lock inside the door
- `action_id`: 6, `message`: Turn on child lock
- `action_id`: 7, `message`: Turn off child lock
- `method_id`: 0, `method`: bluetooth
- `method_id`: 1, `method`: password
- `method_id`: 2, `method`: biological
- `method_id`: 3, `method`: key
- `method_id`: 4, `method`: turntable
- `method_id`: 5, `method`: nfc
- `method_id`: 6, `method`: one-time password
- `method_id`: 7, `method`: two-step verification
- `method_id`: 8, `method`: coercion
- `method_id`: 10, `method`: manual
- `method_id`: 11, `method`: automatic
- `key_id`: 0xc0de0000, `error`: Frequent unlocking with incorrect password
- `key_id`: 0xc0de0001, `error`: Frequent unlocking with wrong fingerprints
- `key_id`: 0xc0de0002, `error`: Operation timeout (password input timeout)
- `key_id`: 0xc0de0003, `error`: Lock picking
- `key_id`: 0xc0de0004, `error`: Reset button is pressed
- `key_id`: 0xc0de0005, `error`: The wrong key is frequently unlocked
- `key_id`: 0xc0de0006, `error`: Foreign body in the keyhole
- `key_id`: 0xc0de0007, `error`: The key has not been taken out
- `key_id`: 0xc0de0008, `error`: Error NFC frequently unlocks
- `key_id`: 0xc0de0009, `error`: Timeout is not locked as required
- `key_id`: 0xc0de000a, `error`: Failure to unlock frequently in multiple ways
- `key_id`: 0xc0de000b, `error`: Unlocking the face frequently fails
- `key_id`: 0xc0de000c, `error`: Failure to unlock the vein frequently
- `key_id`: 0xc0de000d, `error`: Hijacking alarm
- `key_id`: 0xc0de000e, `error`: Unlock inside the door after arming
- `key_id`: 0xc0de000f, `error`: Palmprints frequently fail to unlock
- `key_id`: 0xc0de0010, `error`: The safe was moved
- `key_id`: 0xc0de1000, `error`: The battery level is less than 10%
- `key_id`: 0xc0de1001, `error`: The battery is less than 5%
- `key_id`: 0xc0de1002, `error`: The fingerprint sensor is abnormal
- `key_id`: 0xc0de1003, `error`: The accessory battery is low
- `key_id`: 0xc0de1004, `error`: Mechanical failure

Email me if the values are wrong somewhere. I translated from Chinese [documentation](https://iot.mi.com/new/doc/embedded-development/ble/object-definition).

Example of several automations:

```yaml
automation:
- alias: Doorbell
  trigger:
    platform: state
    entity_id: sensor.ble_1010274797_action
    to: door
  condition:
    condition: template
    value_template: "{{ trigger.to_state.attributes['action_id'] == 3 }}"
  action:
    service: persistent_notification.create
    data_template:
      title: Doorbell
      message: The doorbell is ringing

- alias: Lock Error
  trigger:
    platform: state
    entity_id: sensor.ble_1010274797_action
    to: lock
  condition:
    condition: template
    value_template: "{{ trigger.to_state.attributes['error'] }}"
  action:
    service: persistent_notification.create
    data_template:
      title: Lock ERROR
      message: "{{ trigger.to_state.attributes['error'] }}"

- alias: Open lock
  trigger:
    platform: state
    entity_id: sensor.ble_1010274797_action
    to: lock
  condition:
    condition: template
    value_template: "{{ trigger.to_state.attributes['action_id'] == 0 }}"
  action:
    service: persistent_notification.create
    data_template:
      title: Lock is open
      message: |
        Opening method: {{ trigger.to_state.attributes['method'] }}
        User ID: {{ trigger.to_state.attributes['key_id'] }}
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

With `debug: bluetooth` or debug `debug: mqtt` option you will get advanced log for raw BLE and MQTT data.

With `debug: true` option you will get usual component logs.

```yaml
xiaomi_gateway3:
  debug: true  # you will get HA notification with a link to the logs page
```

You can filter data in the logs and enable auto refresh (in seconds).

```
http://192.168.1.123:8123/c4e99cfc-0c83-4a39-b7f0-278b0e719bd1?q=ble_event&r=2
```
