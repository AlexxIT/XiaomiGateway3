# Xiaomi Gateway 3 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-BuyMeCoffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-YooMoney-8C3FFD.svg)](https://yoomoney.ru/to/41001428278477)

Gateway | Xiaomi Mijia Smart<br>Multi-Mode Gateway | Aqara Hub E1 | Aqara Camera Hub G3
---|---|---|---
China model | **ZNDMWG03LM**<br>![](https://via.placeholder.com/10/00ff00/000000?text=+) supported | **ZHWG16LM**<br>![](https://via.placeholder.com/10/ffff00/000000?text=+) in development | **ZNSXJ13LM**<br>![](https://via.placeholder.com/10/ffff00/000000?text=+) in plans (waiting)
Euro model | **ZNDMWG02LM**<br>![](https://via.placeholder.com/10/00ff00/000000?text=+) supported | **HE1-G01**<br>![](https://via.placeholder.com/10/ff0000/000000?text=+) can't be supported | **CH-H03**<br>![](https://via.placeholder.com/10/ffff00/000000?text=+) don't know yet
Mi Home | **yes** | **yes** | **no**
Aqara Home | **no** | **no** | **yes**
Xiaomi/Aqara Zigbee | **yes** | **yes** |
Xiaomi Bluetooth BLE | **yes** | **no** |
Xiaomi Bluetooth Mesh | **yes** | **no** |

**Real [user](https://github.com/to4ko/myconfig) config with 3 Gateways**

<img src="integrations.png" width="758">

Thanks to [@Serrj](https://community.home-assistant.io/u/serrj-sv/) for [instruction](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) how to enable Telnet on old firmwares. And thanks to an unknown researcher for [instruction](https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709) how to open telnet on new firmwares.

> **Note:** Use another integrations for support:
> 
> - Xiaomi Gateway 2 (DGNWG02LM) - [external link](https://www.home-assistant.io/integrations/xiaomi_aqara/)
> - Xiaomi Gateway EU (DGNWG05LM), Aqara Hub (ZHWG11LM) - [external link](https://openlumi.github.io/)
> - Aqara E1 CN (ZHWG16LM), Aqara G2H (ZNSXJ12LM), Aqara H1 CN (QBCZWG11LM), Aqara M1S CN (ZHWG15LM), Aqara M2 CN (ZHWG12LM), Aqara P3 CN (KTBL12LM) - [external link](https://github.com/niceboygithub/AqaraGateway)

**Attention:** The component is under active development. Breaking changes may appear.

# Table of Contents

- [FAQ](#faq)
- [Requirements](#requirements)
- [Supported Firmwares](#supported-firmwares)
- [Supported Zigbee Devices](#supported-zigbee-devices)
- [Supported BLE Devices](#supported-ble-devices)
- [Supported Bluetooth Mesh Devices](#supported-bluetooth-mesh-devices)
- [Installation](#installation)
- [Configuration](#configuration)
- [Zigbee and BLE performance table](#zigbee-and-ble-performance-table)
- [Advanced config](#advanced-config)
- [Add and remove Zigbee devices](#add-and-remove-zigbee-devices)
- [Add third-party Zigbee devices](#add-third-party-zigbee-devices)
- [Zigbee Home Automation Mode](#zigbee-home-automation-mode)
- [Zigbee2MQTT Mode](#zigbee2mqtt-mode)
- [Handle Button Actions](#handle-button-actions)
- [Handle BLE Locks](#handle-ble-locks)
- [Obtain Mi Home device token](#obtain-mi-home-device-token)
- [Disable Buzzer](#disable-buzzer)
- [Advanced commands](#advanced-commands)
- [How it works](#how-it-works)
- [Troubleshouting](#troubleshooting)
- [Debug mode](#debug-mode)
- [Useful links](#userful-links)

# FAQ

**Q. Does this integration support hubs DGNWG02LM, DGNWG05LM, Aqara Hub...?**  
A. No. The integration only supports ZNDMWG03LM (China version) and ZNDMWG02LM (Euro version).

**Q. Does this integration support Xiaomi Robot Vacuum, Xiaomi Philips Bulb...?**  
A. No. The integration does not support Xiaomi Wi-Fi devices.

**Q. Which Mi Home region is best to use?**  
A. Most devices are supported in the China region. In European regions may not work new Zigbee devices E1/H1/T1-series and some Mesh devices. You can connect Euro Gateway to China region or China Gateway to Euro region if you want.

**Q. What means device beeps?**  
A. Beeps AFTER adding Zigbee devices:
1. No new devices found, the pair is stopped.
2. New device successfully added.
3. Unsupported device model.

Also, if you using hacked motion sensor - the getaway will periodically beeps. You can disable it in integration settings. 

**Q. Does the integration work without internet?**  
A. Partially. The component connects to a hub on the local network. Zigbee devices work without internet. But adding new Zigbee devices to Mi Home requires Internet. Updating BLE device data may not work without Internet.

**Q. Does the integration support non Xiaomi Zigbee devices?**  
A. Yes. There are three ways to connect third party Zigbee devices. All methods have a different set of supported devices. There is no exact supported list. Don't expect absolutely every device on the market to be supported in any of these methods.

**Q. Will the Zigbee devices continue to work in Mi Home?**  
A. Yes. If you do not enable ZHA or z2m mode, the devices will continue to work in Mi Home. And you can use automation in both Mi Home and Hass.

**Q. Do I need to receive a token or enable Telnet manually?**  
A. No. The token is obtained automatically using the login / password from the Mi Home account. Telnet turns on automatically using token.

**Q. Should I open or solder the hub?**  
A. No. Read [supported firmwares](#supported-firmwares) section.

**Q. Should I use ZHA mode?**  
A. You decide. If all of your Zigbee devices are supported in Mi Home, it is best to use it. If you have two hubs - you can use one of them in Mi Home mode, and the second in ZHA mode. Or you can also use the hub in Mi Home mode with Xiaomi devices and a Zigbee USB Dongle for other Zigbee devices.

**Q. How many Zigbee devices does the hub support?**  
A. The hub can connect directly up to 32 battery-powered devices (end devices). And **additionaly** up to 26 powered devices (routers). Other devices on your network can work through routers. The maximum number of devices is unknown. Official Xiaomi documentation writes about 128 devices.

**Q. Does the component support decoupled mode for switches?**  
A. Yes, but it needs to be turned on in the Mi Home app.

**Q. Why does the two-button switch only have one entity action?**  
A. All button clicks are displayed in the status of that one entity.

# Requirements

All requirements are **important** or you may have an unstable operation of the gateway.

- Xiaomi Mijia Smart Multi-Mode Gateway `ZNDMWG03LM` (China) or `ZNDMWG02LM` (Euro)
- Gateway firmware `v1.4.7` and more
- Home Assistant `v2021.7` and more
- **Shared LAN** between Gateway and Hass server. You may use VPN, but both IP-address should be in **same network subnet**!
- **Open ping** (accept ICMP) from Gateway to Router
- **Fixed IP-address** for Gateway on your Router
- Wi-Fi Router settings:
   - **Fixed channel** from 1 to 11
   - Channel width: **20MHz**
   - Authentication: WPA2
   - Group key update interval: **1 hour** and more

With the following settings the operation of the gateway may be **unstable**: different subnets, closed ping to router, Wi-Fi channel 40MHz, WPA3. 

> **Important:** Integration supports gateway on **ORIGINAL** firmware. You don't need to solder, or custom firmware!
>
> Additionally, the integration supports [custom firmware](https://github.com/zvldz/mgl03_fw/tree/main/firmware). The custom firmware works the same way as the original firmware and will not give you new features or support for new devices. Use it only if you know why you need it.

# Supported Firmwares

The component is only tested with these firmware versions:

- v1.5.0_0102 - you **should** use [custom open telnet command](https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709), safe to update

If you have problems with other firmware, don't even ask to fix it.

The component can work with these firmware versions, but they may have bugs: v1.4.7_0063, v1.4.7_0065, v1.4.7_0115, v1.4.7_0160, v1.5.0_0026, v1.5.1_0032.

If your Mi Home doesn't offer to you new firmware - you can [update using telnet](https://github.com/zvldz/mgl03_fw/tree/main/firmware).

Component can block fw updates with **Lock Firmware** switch. Mi Home app will continue to offer you update. But won't be able to install it. It should fail at 0%.

[![Xiaomi Gateway 3 firmware update lock](https://img.youtube.com/vi/9BMoKq19yCI/mqdefault.jpg)](https://www.youtube.com/watch?v=9BMoKq19yCI)

# Supported Zigbee Devices

> **Note:** this devices supported in default (Mi Home) mode. To support devices from other companies, read below.

Tested Devices:
- Aqara Bulb (ZNLDP12LM)
- Aqara Button (WXKG11LM)
- Aqara Cube (MFKZQ01LM)
- Aqara Curtain (ZNCLDJ11LM)
- Aqara Curtain B1 (ZNCLDJ12LM)
- Aqara Door Lock S1 (ZNMS11LM)
- Aqara Door Lock S2 (ZNMS12LM)
- Aqara Door Lock S2 Pro (ZNMS12LM)
- Aqara Door Sensor (MCCGQ11LM)
- Aqara Double Wall Button (WXKG02LM)
- Aqara Double Wall Button D1 (WXKG07LM)
- Aqara Double Wall Switch (QBKG03LM,QBKG12LM)
- Aqara Double Wall Switch D1 (QBKG22LM,QBKG24LM)
- Aqara Double Wall Switch E1 (QBKG39LM,QBKG41LM)
- Aqara Double Wall Switch H1 (WS-EUK02)
- Aqara Double Wall Switch US (WS-USC04)
- Aqara Motion Sensor (RTCGQ11LM)
- Aqara Opple Four Button (WXCJKG12LM)
- Aqara Opple MX480 (XDD13LM)
- Aqara Opple MX650 (XDD12LM)
- Aqara Opple Six Button (WXCJKG13LM)
- Aqara Opple Two Button (WXCJKG11LM)
- Aqara Plug (SP-EUC01)
- Aqara Precision Motion Sensor (RTCGQ13LM)
- Aqara Relay (LLKZMK11LM)
- Aqara Relay T1 (DLKZMK11LM,SSM-U01,SSM-U02)
- Aqara Roller Shade (ZNGZDJ11LM)
- Aqara Roller Shade E1 (ZNJLBL01LM)
- Aqara Shake Button (WXKG12LM)
- Aqara Single Wall Button (WXKG03LM)
- Aqara Single Wall Button D1 (WXKG06LM)
- Aqara Single Wall Switch (QBKG04LM,QBKG11LM)
- Aqara Single Wall Switch D1 (QBKG21LM,QBKG23LM)
- Aqara Single Wall Switch E1 (QBKG38LM,QBKG40LM)
- Aqara Single Wall Switch H1 (WS-EUK01)
- Aqara Socket (QBCZ11LM)
- Aqara TH Sensor (WSDCGQ11LM,WSDCGQ12LM)
- Aqara TVOC Air Quality Monitor (VOCKQJK11LM)
- Aqara Thermostat S2 (KTWKQ03ES)
- Aqara Triple Wall Switch D1 (QBKG25LM,QBKG26LM)
- Aqara Vibration Sensor (DJT11LM)
- Aqara Water Leak Sensor (SJCGQ11LM)
- Honeywell Gas Sensor (JTQJ-BF-01LM/BW)
- Honeywell Smoke Sensor (JTYJ-GD-01LM/BW)
- IKEA Bulb E14 (LED1649C5)
- IKEA Bulb E14 400 lm (LED1536G5)
- IKEA Bulb E27 1000 lm (LED1623G12)
- IKEA Bulb E27 950 lm (LED1546G12)
- IKEA Bulb E27 980 lm (LED1545G12)
- IKEA Bulb GU10 400 lm (LED1537R6,LED1650R5)
- Xiaomi Button (WXKG01LM)
- Xiaomi Door Sensor (MCCGQ01LM)
- Xiaomi Light Sensor (GZCGQ01LM)
- Xiaomi Motion Sensor (RTCGQ01LM)
- Xiaomi Plug (ZNCZ02LM)
- Xiaomi Plug EU (ZNCZ04LM)
- Xiaomi Plug TW (ZNCZ03LM)
- Xiaomi Plug US (ZNCZ12LM)
- Xiaomi TH Sensor (WSDCGQ01LM)

# Supported BLE Devices

**Video DEMO**

[![Xiaomi Rubik's Cube](https://img.youtube.com/vi/4D_vqvUre_0/mqdefault.jpg)](https://www.youtube.com/watch?v=4D_vqvUre_0)

Tested Devices:
- Aqara Door Lock N100 (ZNMS16LM) **Attention:** Zigbee version not supported!
- Aqara Door Lock N200 (ZNMS17LM)
- Honeywell Smoke Alarm (JTYJ-GD-03MI)
- Xiaomi Alarm Clock (CGD1)
- Xiaomi Door Lock (MJZNMS02LM,XMZNMST02YD)
- Xiaomi Door Sensor 2 (MCCGQ02HL)
- Xiaomi Flower Care (HHCCJCY01)
- Xiaomi Flower Pot (HHCCPOT002)
- Xiaomi Magic Cube (XMMF01JQD)
- Xiaomi Mosquito Repellent (WX08ZM)
- Xiaomi Motion Sensor 2 (RTCGQ02LM)
- Xiaomi Night Light 2 (MJYD02YL-A)
- Xiaomi Qingping Door Sensor (CGH1)
- Xiaomi Qingping Motion Sensor (CGPR1)
- Xiaomi Qingping TH Lite (CGDK2)
- Xiaomi Qingping TH Sensor (CGG1)
- Xiaomi Safe Box (BGX-5/X1-3001)
- Xiaomi TH Clock (LYWSD02MMC)
- Xiaomi TH Sensor (LYWSDCGQ/01ZM)
- Xiaomi TH Sensor 2 (LYWSD03MMC)
- Xiaomi Toothbrush T500 (MES601)
- Xiaomi Water Leak Sensor (SJWS01LM)
- Xiaomi ZenMeasure Clock (MHO-C303)
- Xiaomi ZenMeasure TH (MHO-C401)
- Yeelight Button S1 (YLAI003)

XMMF01JQD don't sends edge info, only direction!

Other BLE devices also maybe supported...

BLE devices and their attributes **don't appear immediately**! Data collected and stored at the gateway. After rebooting Hass - data restored from the gateway. Rebooting the gateway will clear the saved data!

# Supported Bluetooth Mesh Devices

Tested Mesh Lights:
- Xiaomi Mesh Bulb (MJDP09YL)
- Xiaomi Mesh Downlight (MJTS01YL/MJTS003)
- Xiaomi Mesh Group (Mesh Group)
- XinGuang XinGuang Smart Light (LIBMDA09X)
- Yeelight Mesh Bulb E14 (YLDP09YL)
- Yeelight Mesh Bulb E27 (YLDP10YL)
- Yeelight Mesh Bulb M2 (YLDP25YL/YLDP26YL)
- Yeelight Mesh Downlight (YLSD01YL)
- Yeelight Mesh Downlight M2 (YLTS02YL/YLTS04YL)
- Yeelight Mesh Spotlight (YLSD04YL)

Tested Mesh Switches:
- PTX Mesh Double Wall Switch (PTX-SK2M)
- PTX Mesh Single Wall Switch (PTX-SK1M)
- PTX Mesh Triple Wall Switch (PTX-SK3M,PTX-TK3/M)
- Xiaomi Mesh Double Wall Switch (DHKG02ZM,ZNKG02HL)
- Xiaomi Mesh Single Wall Switch (ZNKG01HL)
- Xiaomi Mesh Triple Wall Switch (ZNKG03HL/ISA-KG03HL)
- Xiaomi Mesh Wall Switch (DHKG01ZM)
- Xiaomi Mi Smart Electrical Outlet (ZNCZ01ZM)

Other Mesh devices also maybe supported...

# Installation

**Video DEMO**

[![Xiaomi Gateway 3 control from Home Assistant](https://img.youtube.com/vi/CQVSFISC9CE/mqdefault.jpg)](https://www.youtube.com/watch?v=CQVSFISC9CE)

**Method 1.** [HACS](https://hacs.xyz/):

> HACS > Integrations > Plus > **XiaomiGateway3** > Install

**Method 2.** Manually copy `xiaomi_gateway3` folder from [latest release](https://github.com/AlexxIT/XiaomiGateway3/releases/latest) to `/config/custom_components` folder.

# Configuration

**Video DEMO**

[![Mi Cloud authorization in Home Assistant with Xiaomi Gateway 3](https://img.youtube.com/vi/rU_ATCVKx78/mqdefault.jpg)](https://www.youtube.com/watch?v=rU_ATCVKx78)

> Configuration > Integrations > Add Integration > **Xiaomi Gateway3 **

If the integration is not in the list, you need to clear the browser cache.

You need to install integration two times:
1. Cloud version. It used ONLY to load tokens and names for your devices from cloud.
2. Gateway. It adds your gateway and all connected Zigbee, BLE and Mesh devices.

You may skip 1st step if you know token for you Gateway. If you have multiple Gateways - repeat step 2 for each of them.

**ATTENTION:** If you using two Hass with one gateway - you should use same integration version on both of them! 

# Zigbee and BLE performance table

![](zigbee_table.png)

1. To enable stats sensors go to:

   > Configuration > Integrations > Xiaomi Gateway 3 > Options > Zigbee and BLE performance data

2. Install [Flex Table](https://github.com/custom-cards/flex-table-card) from HACS

3. Add new Lovelace tab with **Panel Mode**

4. Add new Lovelace card:
   - [example 1](https://gist.github.com/AlexxIT/120f20eef4f39071e67f698207490db9)
   - [example 2](https://github.com/avbor/HomeAssistantConfig/blob/master/lovelace/views/vi_radio_quality_gw3.yaml)

How it works:

- for each Zigbee and BLE device, a sensor will be created with the time of receiving the last message from this sensor
- there will also be a lot of useful information in the sensor attributes
- for the Gateway, the sensor state shows the uptime of the gateway connection, so you can check the stability of your Wi-Fi
- the `uptime` in gateway sensor attributes means time after reboot gateway
- the `msg_missed` may not always show correct data if you reboot the gate or device
- dash in the `type` means that the device is not directly connected to the hub
- the `parent` can be updated within a few hours

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

**Ignore offline** device status.

```yaml
# /config/customize.yaml
switch.0x158d0003456789_switch:
  ignore_offline: 1  # any non-empty value
```

**Zigbee bulb default transition**.

```yaml
light.0x86bd7fffe000000_light:
  default_transition: 5
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

You need to choose the most similar Xiaomi model for your device from [this file](https://github.com/AlexxIT/XiaomiGateway3/blob/master/custom_components/xiaomi_gateway3/core/zigbee.py).

For example, for a lamp or dimmer - choose an IKEA lamp `ikea.light.led1623g12`.

Sometimes it doesn't work the first time and you need to try pairing again.

The devices added in this way will work even after the Gateway is restarted. They will continue to work without Hass. And they can be used in Mi Home automations.

You can discuss the feature [here](https://github.com/AlexxIT/XiaomiGateway3/issues/44).

# Zigbee Home Automation Mode

You **do not need** to solder or flash the gate. It is ready to work with the ZHA out of the box.

> **Note:** ZHA developers do [not recommend](https://github.com/zigpy/bellows#hardware-requirement) using ZHA with EZSP radios for WiFi-based bridges because of possible stability problems. But a range of users use the gate in this mode without issues.

**Video DEMO**

[![Zigbee Home Automation (ZHA) with Xiaomi Gateway 3 on original firmware without soldering](https://img.youtube.com/vi/AEkiUK7wGbs/mqdefault.jpg)](https://www.youtube.com/watch?v=AEkiUK7wGbs)

[Zigbee Home Automation](https://www.home-assistant.io/integrations/zha/) (ZHA) is a standard Home Assistant component for managing Zigbee devices. It works with various radio modules such as CC2531, Conbee II, Tasmoted Sonoff ZBBridge and others.

**Important:** ZHA component is in active development stage. Don't expect it to work well with all devices.

**Attention: ZHA mode cannot work simultaneously with Mi Home!**

When you turn on ZHA mode - zigbee devices in Mi Home will stop working. Bluetooth devices (BLE and Mesh) will continue to work in Mi Home and Hass.

To switch the mode go to:

> Configuration > Integrations > Xiaomi Gateway 3 > Options > Mode

Zigbee devices will not migrate from Mi Home to ZHA. You will need to pair them again with ZHA.

You can change the operating mode at any time. This mode will flash firmware of Gateway Zigbee chip to a new version with reduced speed, to avoid errors in the data. And flash it back when you switch back to Mi Home mode. Switch back before any Gateway firmware updates via Mi Home.

Thanks to [@zvldz](https://github.com/zvldz) for help with [socat](http://www.dest-unreach.org/socat/).

# Zigbee2MQTT Mode

> **Important:** The zigbee chip of this gateway (EFR32 EZSP v8) is supported in zigbee2mqtt in [experimental mode](https://www.zigbee2mqtt.io/guide/adapters/#experimental). At the moment it is not working well and **not recommended for use**.

**Video DEMO**

[![Xiaomi Gateway 3 with support Zigbee2mqtt in Home Assistant](https://img.youtube.com/vi/esJ0nsqjejc/mqdefault.jpg)](https://www.youtube.com/watch?v=esJ0nsqjejc)

[Zigbee2MQTT](https://www.zigbee2mqtt.io/) is a bigest project that support [hundreds](https://www.zigbee2mqtt.io/information/supported_devices.html) Zigbee devices from different vendors. And can be integrate with a lot of home automation projects.

Unlike the ZHA you should install to your host or Hass.io system: [Mosquitto broker](https://github.com/home-assistant/addons/tree/master/mosquitto) and [Zigbee2MQTT Addon](https://github.com/zigbee2mqtt/hassio-zigbee2mqtt). Also you should setup [MQTT](https://www.home-assistant.io/integrations/mqtt/) integration.

**Attention: Zigbee2MQTT mode cannot work simultaneously with Mi Home!**

When you turn on Zigbee2MQTT mode - zigbee devices in Mi Home will stop working. Bluetooth devices (BLE and Mesh) will continue to work in Mi Home and Hass.

To switch the mode go to:

> Configuration > Integrations > Xiaomi Gateway 3 > Options > Mode

Zigbee devices will not migrate from Mi Home to Zigbee2MQTT. You will need to pair them again.

This mode will flash firmware of Gateway Zigbee chip automatically! And flash it back when you switch back to Mi Home mode. Becuse Zigbee2MQTT support only [new EZSP firmware](https://github.com/Koenkk/zigbee-herdsman/pull/317) and Xiaomi works with old one.

You can use this mode with thank to this peoples:

- [@kirovilya](https://github.com/kirovilya) - developed support EFR32 chips in z2m project
- [@CODeRUS](https://github.com/CODeRUS) and [@zvldz](https://github.com/zvldz) - adapted the script to flash the chip
- [@faronov](https://github.com/faronov) - complied a new version of firmware 

# Handle Button Actions

**Video DEMO**

[![Handling Zigbee buttons with Xiaomi Gateway 3 in Home Assistant](https://img.youtube.com/vi/a8hsNlTErac/mqdefault.jpg)](https://www.youtube.com/watch?v=a8hsNlTErac)

Buttons, vibration sensor, cube, locks and other - create an action entity. The entity changes its **state** for a split second and returns to an empty state. The **attributes** contain useful data, they are not cleared after the event is triggered.

Depending on the button model, its state may be:
- single button: `single`, `double`, `triple`, `quadruple`, `many`, `hold`, `release`, `shake`
- double button: `button_1_single`, `button_2_single`, `button_both_single`, etc.
- triple button: `button_1_single`, `button_12_single`, `button_23_single`, etc.

Your button may not have all of these options! Check available values in `action`-sensor attributes when you interact with button.

```yaml
automation:
- alias: Turn off all lights
  trigger:
  - platform: state
    entity_id: sensor.0x158d0002fa99fd_action  # change to your button
    to: button_1_single  # change to your button state
  action:
  - service: light.turn_off
    entity_id: all
  mode: single
```

# Handle BLE Locks

<img src="bluetooth_lock.png" width="810">

Read more in [wiki](https://github.com/AlexxIT/XiaomiGateway3/wiki/Handle-BLE-Locks).

# Obtain Mi Home device token

**Video DEMO**

[![Mi Cloud authorization in Home Assistant with Xiaomi Gateway 3](https://img.youtube.com/vi/rU_ATCVKx78/mqdefault.jpg)](https://www.youtube.com/watch?v=rU_ATCVKx78)

You can use this integration to **get a token for any of your Xiaomi devices**. You don't need to have Xiaomi Gateway 3. Just install and add the integration, enter the username / password from your Mi Home account. And use the integration settings to view your account's device tokens.

Also you can get:

- **LAN key** for old [Xiaomi Mijia Gateway](https://www.home-assistant.io/integrations/xiaomi_aqara/) (lumi.gateway.v3)
- **room names** for Vacuums that support room with names
- **Bindkey** for BLE devices that has it

<img src="cloud_tokens.png" width="1202">

# Disable Buzzer

This option disable only beeps from hacked motion sensor (5 sec):

> Configuration > Integrations > Xiaomi Gateway 3 > Options > Disable buzzer

# Advanced commands

**Reboot Gateway**

```yaml
script:
  reboot_gateway:
    sequence:
    - service: remote.send_command
      entity_id: remote.0x0123456789abcdef_pair  # change to your gateway
      data:
        command: reboot
```

**Attention:** I don’t know if it’s safe to change the channel and power of the gateway. Use at your own risk.

The information in the attributes of the pair object is updated within a minute!

**Change Zigbee channel**

```yaml
command: channel 15  # I saw values: 11, 15, 20, 25
```

**Change Zigbee TX power**

```yaml
command: power 7  # I saw values: 0, 7, 30
```

# How it works

The component enables **Telnet** on Gateway via [Miio protocol](https://github.com/rytilahti/python-miio).

The component starts the **MQTT Server** on the public port of the Gateway. All the Zigbee logic in the Gateway runs on top of the built-in MQTT Server. By default, access to it is closed from the outside.

**ATTENTION:** Telnet and MQTT work without a password! Do not use this method on public networks.

After rebooting the device, all changes will be reset. The component will launch Telnet and public MQTT every time it detects that they are disabled.

# Troubleshooting

### Can't connect to gateway

- Check [Requirements](#requirements) readme section
- Check if the Gateway really has the IP-address you set in the configuration
- Check if the Gateway really use the MiHome token you set in the configuration. When you add a hub to MiHome - its token changes. The integration only updates tokens when Hass starts. And only if there are no problems with connection to the cloud servers. If there are problems, the old (wrong) token value will be shown.

### Lost connection with Zigbee and Bluetooth devices

- Check [Requirements](#requirements) readme section, gateway and Wi-Fi router settings must be fully matched to all items in the section
- Turn on stat sesors (Configuration > Integrations > Gateway 3 > Configure > Add statisic sensors)
- Check that the connection to the Gateway is not dropped for weeks (`_gateway` sensor value means connection uptime)
- Check that the zigbee error rate is not increasing at a high rate (`zigbee_oe` attribute in `_gateway` sensor, normal rate: 1-2 errors per hour)
- Check that CPU utilisation is within normal values (`load_avg` attribute in `_gateway` sensor (first 3 items), normal value: below 3)
- Check that message skip rate for your zigbee device are not high (`msg_missed` attribute in `_zigbee` sensor)
- Check that your zigbee device is connected via a router, the most stable operation when your devices are connected directly to the gateway (`parent` attribute in `_zigbee` sensor)
- Make sure there are no other electronic devices within 0.5 meter from your Gateway
- Check the distance between the Gateway and the device, greater distances and barriers - the less stable the operation
- Check the gateway zigbee TX power, you can try to increase it if you need (`radio_tx_power` attribute in `_gateway` sensor)

# Debug mode

Logging can be setup from:

**1. Integration config (GUI)**

> Configuration > Integrations > Xiaomi Gateway 3 > Configure > Debug

Shows only component logs. The link to the logs is always random and will apear in Notifications.

By adding params to url, you can filter data in the logs, enable auto refresh (in seconds) and tail last lines.

```
http://192.168.1.123:8123/c4e99cfc-0c83-4a39-b7f0-278b0e719bd1?q=ble_event&r=2&t=100
```

**2. Integration config (YAML)**

Component can log different debug events from different gateways. You can set global `debug_mode` for all gateways or config custom modes for custom gateways from GUI.

Recommended config:

```yaml
xiaomi_gateway3:
  logger:
    filename: xiaomi_gateway3.log  # default empty
    propagate: False  # if False - disable log to home-assistant.log and console, default True
    max_bytes: 100000000  # file size, default 0
    backup_count: 3  # file rotation count, default 0
    debug_mode: true,miio,mqtt  # global modes for all gateways, default empty
```

Additional settings

```yaml
    level: debug  # default
    mode: a  # a - append to file, w - write new file, default
    format: "%(asctime)s %(message)s"  # default
```

**3. Hass default config**

You can set custom modes for custom gateways from GUI. Witout custom modes you won't see gateways logs.

```yaml
logger:
  logs:
    custom_components.xiaomi_gateway3: debug
```

# Useful links

- [Russian Telegram Community](https://t.me/xiaomi_gw_v3_hack)
- [Italian Telegram Community](https://t.me/HassioHelp)
- [Russian video about instal integration](https://youtu.be/FVWfjE5tx2g)
- [Russian article about flash gateway](https://simple-ha.ru/posts/261)
- [Home Assistant Community](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586)
