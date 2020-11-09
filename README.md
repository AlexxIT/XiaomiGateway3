# Xiaomi Gateway 3 integration for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-Coffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-Yandex-red.svg)](https://money.yandex.ru/to/41001428278477)

Control Zigbee devices from Home Assistant with **Xiaomi Gateway 3 (ZNDMWG03LM)** on original firmware.

**ATTENTION:** The component **does not work with new firmware versions**. Don't update your gateway! Check [supported firmwares](#supported-firmwares).

Gateway support **Zigbee 3**, **Bluetooth Mesh** and **HomeKit**.

This method does not change the device firmware. Gateway continues to work with Mi Home and HomeKit.

**Real [user](https://github.com/to4ko/myconfig) config with 3 Gateways**

<img src="integrations.png" width="758">

Thanks to [@Serrj](https://community.home-assistant.io/u/serrj-sv/) for [instruction](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) how to enable Telnet on this device.

**Important:** This component does not work with:
 - Xiaomi Gateway 2 (DGNWG02LM, lumi.gateway.v3) - use [this](https://www.home-assistant.io/integrations/xiaomi_aqara/) component
 - Xiaomi Gateway EU (DGNWG05LM, lumi.gateway.mieu01)

**Attention:** The component is under active development. Breaking changes may appear.

# Table of Contents

- [FAQ](#faq)
- [Supported Firmwares](#supported-firmwares)
- [Supported Zigbee Devices](#supported-zigbee-devices)
- [Supported BLE Devices](#supported-ble-devices)
- [Supported Bluetooth Mesh Devices](#supported-bluetooth-mesh-devices)
- [Install](#install)
- [Config](#config)
- [Advanced config](#advanced-config)
- [Add and remove Zigbee devices](#add-and-remove-zigbee-devices)
- [Add third-party Zigbee devices](#add-third-party-zigbee-devices)
- [Zigbee Home Automation Mode](#zigbee-home-automation-mode)
- [Handle Button Actions](#handle-button-actions)
- [Handle BLE Locks](#handle-ble-locks)
- [Obtain Mi Home device token](#obtain-mi-home-device-token)
- [Disable Buzzer](#disable-buzzer)
- [Advanced commands](#advanced-commands)
- [How it works](#how-it-works)
- [Debug mode](#debug-mode)

# FAQ

**Q. Can Xiaomi close support for this integration in firmware updates?**  
A. Yes, they can and are already doing it. But if you have a worked hub and you do not update it, it will continue to work. Component can block fw updates with **Lock Firmware** switch.

**Q. Does this integration support hubs DGNWG02LM, DGNWG05LM, Aqara Hub...?**  
A. No. The integration only supports ZNDMWG03LM.

**Q. Does this integration support Xiaomi Robot Vacuum, Xiaomi Philips Bulb...?**  
A. No. The integration does not support Xiaomi Wi-Fi devices.

**Q. Does the integration work without internet?**  
A. Partially. The component connects to a hub on the local network. Zigbee devices work without internet. But adding new Zigbee devices to Mi Home requires Internet. Updating BLE device data may not work without Internet.

**Q. Does the integration support non Xiaomi Zigbee devices?**  
A. Yes. There are two ways to connect third party Zigbee devices. The first method allows devices to work in both Mi Home and Hass at the same time. The second method (ZHA) disconnects the hub from Mi Home and only works with Hass. Both methods have a different set of supported devices. There is no exact supported list. Don't expect absolutely every device on the market to be supported in any of these methods.

**Q. Will the Zigbee devices continue to work in Mi Home?**  
A. Yes. If you do not enable ZHA mode, the devices will continue to work in Mi Home. And you can use automation in both Mi Home and Hass.

**Q. Do I need to receive a token or enable Telnet manually?**  
A. No. The token is obtained automatically using the login / password from the Mi Home account. Telnet turns on automatically using token.

**Q. Should I open or solder the hub?**  
A. Depends on the firmware version. Read [supported firmwares](#supported-firmwares) section.

**Q. Should I use ZHA mode?**  
A. You decide. If all of your Zigbee devices are supported in Mi Home, it is best not to enable ZHA. If you have two hubs - you can use one of them in Mi Home mode, and the second in ZHA mode. Or you can also use the hub in Mi Home mode with Xiaomi devices and a Zigbee USB Dongle for other Zigbee devices.

**Q. How many Zigbee devices does the hub support?**  
A. The hub can connect directly up to 32 battery-powered devices (end devices). And **additionaly** up to 26 powered devices (routers). Other devices on your network can work through routers. The maximum number of devices is unknown. Official Xiaomi documentation writes about 128 devices.

**Q. Does the component support decoupled mode for switches?**  
A. Yes, but it needs to be turned on in the Mi Home app.

**Q. Why does the two-button switch only have one entity action?**  
A. All button clicks are displayed in the status of that one entity.

# Supported Firmwares

**Attention:** Starting from 2020.10, there is a high chance of buying any version of the gateway with "bad" firmware. Only soldering will be able to open Telnet.

Instruction for downgrading firmware by soldering: [read more](https://github.com/AlexxIT/XiaomiGateway3/issues/87#issuecomment-719467858).

Component can block fw updates with **Lock Firmware** switch.

[![Xiaomi Gateway 3 firmware update lock](https://img.youtube.com/vi/9BMoKq19yCI/mqdefault.jpg)](https://www.youtube.com/watch?v=9BMoKq19yCI)

**ZNDMWG03LM (Chinese version, US plug)**
- v1.4.4_0003 - factory firmware, supported
- v1.4.5_0012 - factory firmware, supported
- v1.4.5_0016 - safe to update, supported
- v1.4.6_0012 - safe to update, supported
- v1.4.6_0030 - was available in summer 2020, now unavailable, supported
- v1.4.6_0043 - **factory firmware from 2020.10, not supported** (telnet has a password)
- v1.4.7_0040, v1.4.7_0063, v1.4.7_0065 - **not supported** (telnet cannot be opened)

**ZNDMWG02LM (Euro version, no plug)**
- v1.4.6_0043 - factory firmware, **not supported** (telnet has a password)

# Supported Zigbee Devices

Tested Devices:
- Aqara Bulb (ZNLDP12LM)
- Aqara Button (WXKG11LM,WXKG12LM)
- Aqara Single Wall Button (WXKG03LM)
- Aqara Double Wall Button (WXKG02LM)
- Aqara Cube (MFKZQ01LM)
- Aqara Curtain (ZNCLDJ11LM)
- Aqara B1 Curtain (ZNCLDJ12LM)
- Aqara Door Sensor (MCCGQ11LM)
- Aqara Motion Sensor (RTCGQ11LM)
- Aqara Relay (LLKZMK11LM)
- Aqara Roller Shade (ZNGZDJ11LM)
- Aqara Socket (QBCZ11LM)
- Aqara TH Sensor (WSDCGQ11LM,WSDCGQ12LM)
- Aqara Vibration Sensor (DJT11LM)
- Aqara Wall Single Switch (QBKG11LM,QBKG04LM)
- Aqara Wall Double Switch (QBKG12LM,QBKG03LM)
- Aqara Water Leak Sensor (SJCGQ11LM)
- Aqara Opple Two Button (WXCJKG11LM)
- Aqara Opple Four Button (WXCJKG12LM)
- Aqara Opple Six Button (WXCJKG13LM)
- Aqara D1 Single Wall Button (WXKG06LM)
- Aqara D1 Double Wall Button (WXKG07LM)
- Aqara D1 Wall Single Switch (QBKG21LM,QBKG23LM)
- Aqara D1 Wall Double Switch (QBKG22LM,QBKG24LM)
- Aqara D1 Wall Triple Switch (QBKG25LM,QBKG26LM)
- Honeywell Gas Sensor (JTQJ-BF-01LM/BW)
- Honeywell Smoke Sensor (JTYJ-GD-01LM/BW)
- IKEA Bulb E14 400 lm (LED1536G5,LED1649C5)
- IKEA Bulb E27 950 lm (LED1546G12)
- IKEA Bulb E27 980 lm (LED1545G12)
- IKEA Bulb E27 1000 lm (LED1623G12)
- IKEA Bulb GU10 400 lm (LED1650R5,LED1537R6)
- Xiaomi Button (WXKG01LM)
- Xiaomi Door Sensor (MCCGQ01LM)
- Xiaomi Light Sensor (GZCGQ01LM)
- Xiaomi Motion Sensor (RTCGQ01LM)
- Xiaomi Plug (ZNCZ02LM,ZNCZ03LM,ZNCZ04LM,ZNCZ12LM)
- Xiaomi TH Sensor (WSDCGQ01LM)

Currently supported, but not tested other Xiaomi and Aqara Zibee devices officially supported by the Gateway. Check list [here](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/core/utils.py).

# Supported BLE Devices

**Video DEMO**

[![Xiaomi Rubik's Cube](https://img.youtube.com/vi/4D_vqvUre_0/mqdefault.jpg)](https://www.youtube.com/watch?v=4D_vqvUre_0)

Tested Devices:
- Aqara Door Lock N100 (ZNMS16LM)
- Xiaomi Alarm Clock (CGD1)
- Xiaomi Door Sensor 2 (MCCGQ02HL)
- Xiaomi Flower Care (HHCCJCY01)
- Xiaomi Loock Smart Lock
- Xiaomi Mosquito Repellent (WX08ZM)
- Xiaomi Rubik's Cube (XMMF01JQD) - don't sends edge info, only direction!
- Xiaomi TH Clock (LYWSD02MMC)
- Xiaomi TH Sensor (LYWSDCGQ/01ZM)
- Xiaomi TH Sensor 2 (LYWSD03MMC)
- Xaiomi ZenMeasure Clock (MHO-C303)

Other BLE devices also maybe supported...

Kettles and scooters are not BLE devices. It is not known whether the gateway can work with them. Currently not supported.

BLE devices and their attributes **don't appear immediately**! Data collected and stored at the gateway. After rebooting Hass - data restored from the gateway. Rebooting the gateway will clear the saved data!

# Supported Bluetooth Mesh Devices

Tested Devices:
- Xiaomi Mesh Bulb (MJDP09YL)
- Yeelight Mesh Bulb M2 (YLDP25YL/YLDP26YL)

Other Mesh devices also maybe supported...

# Install

**Video DEMO**

[![Xiaomi Gateway 3 control from Home Assistant](https://img.youtube.com/vi/CQVSFISC9CE/mqdefault.jpg)](https://www.youtube.com/watch?v=CQVSFISC9CE)

You can install component with HACS custom repo ([example](https://github.com/AlexxIT/SonoffLAN#install-with-hacs)): `AlexxIT/XiaomiGateway3`.

Or manually copy `xiaomi_gateway3` folder from [latest release](https://github.com/AlexxIT/XiaomiGateway3/releases/latest) to `custom_components` folder in your config folder.

# Config

**Video DEMO**

[![Mi Cloud authorization in Home Assistant with Xiaomi Gateway 3](https://img.youtube.com/vi/rU_ATCVKx78/mqdefault.jpg)](https://www.youtube.com/watch?v=rU_ATCVKx78)

With GUI. Configuration > Integration > Xiaomi Gateway 3.

If the integration is not in the list, you need to clear the browser cache.

# Advanced config

Support custom occupancy timeout for motion sensor and invert state for door sensor (for DIY purposes).

Config through built-in [customizing](https://www.home-assistant.io/docs/configuration/customizing-devices/) UI or YAML.

[![Xiaomi Gateway 3 occupancy timeout settings in Home Assistant](https://img.youtube.com/vi/2EeKnF2uvjo/mqdefault.jpg)](https://www.youtube.com/watch?v=2EeKnF2uvjo)

It's important to add these lines to your `configuration.yaml`. Otherwise, changes to the UI will not be read when you restart Home Assistant.

```yaml
homeassistant:
  customize: !include customize.yaml
```

To enable customizing UI, you need to enable **Advanced Mode** in your user profile.

**Occupancy timeout** for moving sensor.

![](occupancy_timeout.png)

- a **simple timer** starts every time a person moves
- the **progressive timer** starts with a new value with each new movement of the person, the more you move - the longer the timer
- **fast back timer** starts with doubled value if the person moves immediately after the timer is off

```yaml
# /config/customize.yaml
binary_sensor.0x158d0003456789_motion:
  occupancy_timeout: 180  # simple mode
binary_sensor.0x158d0003456788_motion:
  occupancy_timeout: -120  # fast back mode
binary_sensor.0x158d0003456787_motion:
  occupancy_timeout: [-120, 240, 300]  # progressive timer
binary_sensor.0x158d0003456786_motion:
  occupancy_timeout: 1  # for hacked 5 sec sensors
```

**Invert state** for contact sensor.

```yaml
# /config/customize.yaml
binary_sensor.0x158d0003456789_contact:
  invert_state: 1  # any non-empty value will reverse the logic
```

# Add and remove Zigbee devices

To enter the pairing mode, turn on the switch **Xiaomi Gateway 3 Pair**. Pairing lasts 60 seconds.

After successfully adding the device, the Gateway will sound two long beeps.

If the addition was unsuccessful, for example, an unsupported device, the Gateway will sound three short beeps.

To delete a device from Hass and from Gateway - you need to rename device to **delete**. Just the device, not its objects!

# Add third-party Zigbee devices

**Video DEMO**

[![Control non Xiaomi zigbee devices from Xiaomi Gateway 3](https://img.youtube.com/vi/hwtBPMtMnKo/mqdefault.jpg)](https://www.youtube.com/watch?v=hwtBPMtMnKo)

**Attention 1:** Only devices similar to Xiaomi devices will work!

**Attention 2:** After the first pairing, Mi Home remembers the selected device model. And with the next pairings, it will show old interface, even if you change the model. Hass will take the new device model on the next pairings.

To add a custom device, you need to call the service `remote.send_command` with params:

```yaml
entity_id: remote.0x680ae2fffe123456_pair  # change to your Gateway remote
command: pair
device: ikea.light.led1623g12  # change to your device model
```

You need to choose the most similar Xiaomi model for your device from [this file](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/core/utils.py).

For example, for a lamp or dimmer - choose an IKEA lamp `ikea.light.led1623g12`.

Sometimes it doesn't work the first time and you need to try pairing again.

The devices added in this way will work even after the Gateway is restarted. They will continue to work without Hass. And they can be used in Mi Home automations.

You can discuss the feature [here](https://github.com/AlexxIT/XiaomiGateway3/issues/44).

# Zigbee Home Automation Mode

**Video DEMO**

[![Zigbee Home Automation (ZHA) with Xiaomi Gateway 3 on original firmware without soldering](https://img.youtube.com/vi/AEkiUK7wGbs/mqdefault.jpg)](https://www.youtube.com/watch?v=AEkiUK7wGbs)

[Zigbee Home Automation](https://www.home-assistant.io/integrations/zha/) (ZHA) is a standard Home Assistant component for managing Zigbee devices. It works with various radio modules such as CC2531, Conbee II, Tasmoted Sonoff ZBBridge and others.

**Important:** ZHA component is in early development stage. Don't expect it to work well with all devices.

**Attention: ZHA mode cannot work simultaneously with Mi Home!**

When you turn on ZHA mode - zigbee devices in Mi Home will stop working. Bluetooth devices will continue to work.

To switch the mode - delete the old integration and configure the new one in a different mode. Zigbee devices will not migrate from Mi Home to ZHA. You will need to pair them again with ZHA.

You can change the operating mode at any time. Just remove the old integration and set up the new one. Your gateway firmware does not change! Just reboot the gateway and it is back in stock.

When switching from ZHA to Mi Home mode - restart the gateway. When switching from Mi Home to ZHA - no reboot required.

Thanks to [@zvldz](https://github.com/zvldz) for help with [socat](http://www.dest-unreach.org/socat/).

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

Write me if the values are wrong somewhere. I translated from Chinese [documentation](https://iot.mi.com/new/doc/embedded-development/ble/object-definition).

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

# Obtain Mi Home device token

**Video DEMO**

[![Mi Cloud authorization in Home Assistant with Xiaomi Gateway 3](https://img.youtube.com/vi/rU_ATCVKx78/mqdefault.jpg)](https://www.youtube.com/watch?v=rU_ATCVKx78)

You can use this integration to **get a token for any of your Xiaomi devices**. You don't need to have Xiaomi Gateway 3. Just install and add the integration, enter the username / password from your Mi Home account. And use the integration settings to view your account's device tokens.

# Disable Buzzer

If you have a hacked motion sensor, the gateway will beep periodically.

The gateway has an application that handle the **button, LED and beeper**. This option can turn off this application.

**Attention:** I don't know what else this app does and will the gateway work fine without it.

```yaml
xiaomi_gateway3:
  buzzer: off
```

To cancel this changes - disable this option and restart the gateway. The application will continue to work again.

# Advanced commands

```yaml
script:
  reboot_gateway:
    sequence:
    - service: remote.send_command
      entity_id: remote.0x0123456789abcdef_pair  # change to your gateway
      command: reboot
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

You can filter data in the logs, enable auto refresh (in seconds) and tail last lines.

```
http://192.168.1.123:8123/c4e99cfc-0c83-4a39-b7f0-278b0e719bd1?q=ble_event&r=2&t=100
```