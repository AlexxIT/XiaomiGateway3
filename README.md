# Xiaomi Gateway 3 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/custom-components/hacs)
[![Donate](https://img.shields.io/badge/donate-BuyMeCoffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-YooMoney-8C3FFD.svg)](https://yoomoney.ru/to/41001428278477)

Control Zigbee devices from Home Assistant with **Xiaomi Gateway 3 (ZNDMWG03LM and ZNDMWG02LM)** on original firmware.

Gateway support **Zigbee 3**, **Bluetooth Mesh** and **HomeKit**.

This method does not change the device firmware. Gateway continues to work with Mi Home and HomeKit.

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

# Supported Devices

The integration can work in two modes:

**Mi Home (default)**

- Support Xiaomi/Aqara Zigbee devices simultaneously in Mi Home and Hass
- Support some Zigbee devices of other brands only in Hass
- Support Xiaomi BLE devices simultaneously in Mi Home and Hass
- Support Xiaomi Mesh devices simultaneously in Mi Home and Hass

**Zigbee Home Automation (ZHA)**

- Support for Zigbee devices of hundreds of brands only in Hass
- Support Xiaomi BLE devices simultaneously in Mi Home and Hass
- Support Xiaomi Mesh devices simultaneously in Mi Home and Hass

Zigbee devices in ZHA mode doesn't controlled by this integration!

Other Zigbee, BLE and Mesh devices not from the list below also may work with limited support of functionality. 

Every device has **default entities** and **optional entities**. For enable optional entities goto:

> Configuration > Integrations > Xiaomi Gateway 3 > Configure  
> Fill in the entities names to field with any delimiter, e.g. comma or space.  
> Check supported entities names in list below.

Some BLE devices have no known default entities (asterisk in the list). Their entities appear when receiving data from the devices.

Some BLE devices may or may not have battery data depending on the device firmware.

Gateway entity shows connection state to gateway. It has many useful information in attributes.

Zigbee and BLE devices has optional `zigbee` and `ble` that shows `last_seen` time in state and may useful intormation in attributes.

Every device has support level (column S):

- 5 - The device can do everything it can do
- 4 - The device works well, missing some settings
- 3 - The device works, but it is missing some functionality
- empty - Unknown level, but device may work well
- 1/2 - The device doesn't work well (they don't show in the table)

<!--supported-->
## Supported Gateways

Total devices: 2

Brand|Name|Model|Default entities|Optional entities|S
---|---|---|---|---|---
Aqara|Hub E1 (CN)|[ZHWG16LM](https://home.miot-spec.com/s/lumi.gateway.aqcn02)|command, data, gateway||3
Xiaomi|Gateway 3|[ZNDMWG03LM](https://home.miot-spec.com/s/lumi.gateway.mgl03)|alarm, command, data, gateway|cloud_link, led|5

## Supported Xiaomi Zigbee

Total devices: 71

Brand|Name|Model|Default entities|Optional entities|S
---|---|---|---|---|---
Aqara|Bulb|[ZNLDP12LM](https://home.miot-spec.com/s/lumi.light.aqcn02)|light|zigbee, power_on_state|
Aqara|Button|[WXKG11LM](https://home.miot-spec.com/s/lumi.remote.b1acn01)|action, battery|zigbee, battery_percent|
Aqara|Cube|[MFKZQ01LM](https://home.miot-spec.com/s/lumi.sensor_cube.aqgl01)|action, battery|zigbee, battery_percent|3
Aqara|Curtain|[ZNCLDJ11LM](https://home.miot-spec.com/s/lumi.curtain)|motor|zigbee|
Aqara|Curtain B1|[ZNCLDJ12LM](https://home.miot-spec.com/s/lumi.curtain.hagl04)|motor, battery|zigbee|
Aqara|Door Lock S1|[ZNMS11LM](https://home.miot-spec.com/s/lumi.lock.aq1)|action, battery, key_id, lock|zigbee|
Aqara|Door Lock S2|[ZNMS12LM](https://home.miot-spec.com/s/lumi.lock.acn02)|action, battery, key_id, lock|zigbee|
Aqara|Door Lock S2 Pro|[ZNMS12LM*](https://home.miot-spec.com/s/lumi.lock.acn03)|action, lock, door, battery, key_id|zigbee|
Aqara|Door Sensor|[MCCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_magnet.aq2)|contact, battery|zigbee, battery_percent|
Aqara|Double Wall Button|[WXKG02LM](https://home.miot-spec.com/s/lumi.sensor_86sw2.es1)|action, battery|zigbee, battery_percent|
Aqara|Double Wall Button D1|[WXKG07LM](https://home.miot-spec.com/s/lumi.remote.b286acn02)|action, battery|zigbee, battery_percent|
Aqara|Double Wall Button E1|[WXKG17LM](https://home.miot-spec.com/s/lumi.remote.acn004)|action, battery|zigbee|
Aqara|Double Wall Switch|[QBKG03LM](https://home.miot-spec.com/s/lumi.ctrl_neutral2)|channel_1, channel_2, action|zigbee|
Aqara|Double Wall Switch|[QBKG12LM](https://home.miot-spec.com/s/lumi.ctrl_ln2.aq1)|channel_1, channel_2, power, action|zigbee, energy|
Aqara|Double Wall Switch D1|[QBKG22LM](https://home.miot-spec.com/s/lumi.switch.b2lacn02)|channel_1, channel_2, action|zigbee|
Aqara|Double Wall Switch D1|[QBKG24LM](https://home.miot-spec.com/s/lumi.switch.b2nacn02)|channel_1, channel_2, power, action|zigbee, energy|
Aqara|Double Wall Switch E1|[QBKG39LM](https://home.miot-spec.com/s/lumi.switch.b2lc04)|channel_1, channel_2, action|zigbee, smart_1, smart_2, led, power_on_state, mode|5
Aqara|Double Wall Switch E1|[QBKG41LM](https://home.miot-spec.com/s/lumi.switch.b2nc01)|channel_1, channel_2, action|zigbee|
Aqara|Double Wall Switch H1|[WS-EUK02](https://home.miot-spec.com/s/lumi.switch.l2aeu1)|channel_1, channel_2, action|zigbee|
Aqara|Double Wall Switch US|[WS-USC04](https://home.miot-spec.com/s/lumi.switch.b2naus01)|channel_1, channel_2, action, energy, power|zigbee|
Aqara|Motion Sensor|[RTCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_motion.aq2)|motion, illuminance, battery|zigbee, battery_percent|
Aqara|Opple Four Button|[WXCJKG12LM](https://home.miot-spec.com/s/lumi.remote.b486opcn01)|action, battery|zigbee, battery_percent|
Aqara|Opple MX480|[XDD13LM](https://home.miot-spec.com/s/lumi.light.cwopcn03)|light|zigbee|
Aqara|Opple MX650|[XDD12LM](https://home.miot-spec.com/s/lumi.light.cwopcn02)|light|zigbee|
Aqara|Opple Six Button|[WXCJKG13LM](https://home.miot-spec.com/s/lumi.remote.b686opcn01)|action, battery|zigbee, battery_percent|
Aqara|Opple Two Button|[WXCJKG11LM](https://home.miot-spec.com/s/lumi.remote.b286opcn01)|action, battery|zigbee, battery_percent|
Aqara|Plug|[SP-EUC01](https://home.miot-spec.com/s/lumi.plug.maeu01)|switch, energy, power|zigbee, led, power_on_state|5
Aqara|Precision Motion Sensor|[RTCGQ13LM](https://home.miot-spec.com/s/lumi.motion.agl04)|motion, battery|zigbee, sensitivity, battery_low|4
Aqara|Relay|[LLKZMK11LM](https://home.miot-spec.com/s/lumi.relay.c2acn01)|channel_1, channel_2, current, power, voltage, action|zigbee, energy, interlock|
Aqara|Relay T1|[DLKZMK11LM](https://home.miot-spec.com/s/lumi.switch.n0acn2)|switch, energy, power|zigbee, led, power_on_state|5
Aqara|Relay T1|[SSM-U01](https://home.miot-spec.com/s/lumi.switch.n0agl1)|switch, energy, power|zigbee, led, power_on_state|5
Aqara|Relay T1|[SSM-U02](https://home.miot-spec.com/s/lumi.switch.l0agl1)|switch|zigbee, chip_temperature|
Aqara|Roller Shade|[ZNGZDJ11LM](https://home.miot-spec.com/s/lumi.curtain.aq2)|motor|zigbee|
Aqara|Roller Shade E1|[ZNJLBL01LM](https://home.miot-spec.com/s/lumi.curtain.acn002)|motor, battery|zigbee, fault, motor_reverse, battery_low, battery_voltage, battery_charging, motor_speed|5
Aqara|Shake Button|[WXKG12LM](https://home.miot-spec.com/s/lumi.sensor_switch.aq3)|action, battery|zigbee, battery_percent|
Aqara|Single Wall Button|[WXKG03LM](https://home.miot-spec.com/s/lumi.remote.b186acn01)|action, battery|zigbee, battery_percent|
Aqara|Single Wall Button D1|[WXKG06LM](https://home.miot-spec.com/s/lumi.remote.b186acn02)|action, battery|zigbee, battery_percent|
Aqara|Single Wall Button E1|[WXKG16LM](https://home.miot-spec.com/s/lumi.remote.acn003)|action, battery|zigbee|
Aqara|Single Wall Switch|[QBKG04LM](https://home.miot-spec.com/s/lumi.ctrl_neutral1)|switch, action|zigbee|
Aqara|Single Wall Switch|[QBKG11LM](https://home.miot-spec.com/s/lumi.ctrl_ln1.aq1)|switch, power, energy, action|zigbee|
Aqara|Single Wall Switch D1|[QBKG21LM](https://home.miot-spec.com/s/lumi.switch.b1lacn02)|switch, action|zigbee|
Aqara|Single Wall Switch D1|[QBKG23LM](https://home.miot-spec.com/s/lumi.switch.b1nacn02)|switch, power, energy, action|zigbee|
Aqara|Single Wall Switch E1|[QBKG38LM](https://home.miot-spec.com/s/lumi.switch.b1lc04)|switch, action|zigbee, smart, led, power_on_state, mode|5
Aqara|Single Wall Switch E1|[QBKG40LM](https://home.miot-spec.com/s/lumi.switch.b1nc01)|switch, action|zigbee|
Aqara|Single Wall Switch H1|[WS-EUK01](https://home.miot-spec.com/s/lumi.switch.l1aeu1)|switch, action|zigbee|
Aqara|TH Sensor|[WSDCGQ11LM](https://home.miot-spec.com/s/lumi.weather)|temperature, humidity, battery, pressure|zigbee, battery_percent|
Aqara|TH Sensor|[WSDCGQ12LM](https://home.miot-spec.com/s/lumi.sensor_ht.agl02)|temperature, humidity, battery, pressure|zigbee, battery_percent|
Aqara|TVOC Air Quality Monitor|[VOCKQJK11LM](https://home.miot-spec.com/s/lumi.airmonitor.acn01)|temperature, humidity, tvoc, battery|zigbee, battery_low, display_unit|5
Aqara|Thermostat S2|[KTWKQ03ES](https://home.miot-spec.com/s/lumi.airrtc.tcpecn02)|climate|zigbee|
Aqara|Triple Wall Switch D1|[QBKG25LM](https://home.miot-spec.com/s/lumi.switch.l3acn3)|channel_1, channel_2, channel_3, action|zigbee|
Aqara|Triple Wall Switch D1|[QBKG26LM](https://home.miot-spec.com/s/lumi.switch.n3acn3)|channel_1, channel_2, channel_3, power, voltage, action|zigbee, energy|
Aqara|Wall Outlet|[QBCZ11LM](https://home.miot-spec.com/s/lumi.ctrl_86plug.aq1)|outlet, power|zigbee, energy|
Aqara|Water Leak Sensor|[SJCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_wleak.aq1)|moisture, battery|zigbee, battery_percent|
Honeywell|Gas Sensor|[JTQJ-BF-01LM/BW](https://home.miot-spec.com/s/lumi.sensor_natgas)|gas_density, gas|zigbee, sensitivity|4
Honeywell|Smoke Sensor|[JTYJ-GD-01LM/BW](https://home.miot-spec.com/s/lumi.sensor_smoke)|smoke_density, smoke, battery|zigbee, battery_percent|
IKEA|Bulb E14|[LED1649C5](https://home.miot-spec.com/s/ikea.light.led1649c5)|light|zigbee|
IKEA|Bulb E14 400 lm|[LED1536G5](https://home.miot-spec.com/s/ikea.light.led1536g5)|light|zigbee|
IKEA|Bulb E27 1000 lm|[LED1623G12](https://home.miot-spec.com/s/ikea.light.led1623g12)|light|zigbee|
IKEA|Bulb E27 950 lm|[LED1546G12](https://home.miot-spec.com/s/ikea.light.led1546g12)|light|zigbee|
IKEA|Bulb E27 980 lm|[LED1545G12](https://home.miot-spec.com/s/ikea.light.led1545g12)|light|zigbee|
IKEA|Bulb GU10 400 lm|[LED1537R6](https://home.miot-spec.com/s/ikea.light.led1537r6)|light|zigbee|
IKEA|Bulb GU10 400 lm|[LED1650R5](https://home.miot-spec.com/s/ikea.light.led1650r5)|light|zigbee|
Xiaomi|Button|[WXKG01LM](https://home.miot-spec.com/s/lumi.sensor_switch)|action, battery|zigbee, battery_percent|
Xiaomi|Door Sensor|[MCCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_magnet)|contact, battery|zigbee, battery_percent|
Xiaomi|Light Sensor|[GZCGQ01LM](https://home.miot-spec.com/s/lumi.sen_ill.mgl01)|illuminance, battery|zigbee, battery_voltage|5
Xiaomi|Motion Sensor|[RTCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_motion)|motion, battery|zigbee, battery_percent|
Xiaomi|Plug|[ZNCZ02LM](https://home.miot-spec.com/s/lumi.plug)|plug, power|zigbee, energy, chip_temperature, poweroff_memory, charge_protect, led, max_power|5
Xiaomi|Plug EU|[ZNCZ04LM](https://home.miot-spec.com/s/lumi.plug.mmeu01)|plug, power, voltage|zigbee, energy|
Xiaomi|Plug TW|[ZNCZ03LM](https://home.miot-spec.com/s/lumi.plug.mitw01)|plug, power|zigbee, energy|
Xiaomi|Plug US|[ZNCZ12LM](https://home.miot-spec.com/s/lumi.plug.maus01)|plug, power|zigbee, energy|
Xiaomi|TH Sensor|[WSDCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_ht)|temperature, humidity, battery|zigbee, battery_percent|

## Supported Other Zigbee

Total devices: 6

Brand|Name|Model|Default entities|Optional entities|S
---|---|---|---|---|---
BlitzWolf|Plug|[BW-SHP13](https://www.zigbee2mqtt.io/supported-devices/#s=BW-SHP13)|plug, current, power, voltage|zigbee, power_on_state, energy|5
IKEA|Bulb E27 1000 lm|[LED1623G12](https://www.zigbee2mqtt.io/supported-devices/#s=LED1623G12)|light|zigbee|3
Sonoff|Mini|[ZBMINI](https://www.zigbee2mqtt.io/supported-devices/#s=ZBMINI)|switch|zigbee|5
Sonoff|Motion Sensor|[SNZB-03](https://www.zigbee2mqtt.io/supported-devices/#s=SNZB-03)|motion|zigbee|3
Unknown|Dimmer|[LXZ8-02A](https://www.zigbee2mqtt.io/supported-devices/#s=LXZ8-02A)|light|zigbee|3
UseeLink|Power Strip|[SM-SO306E](https://www.zigbee2mqtt.io/supported-devices/#s=SM-SO306E)|channel_1, channel_2, channel_3, channel_4, usb|zigbee, power_on_state|5

## Supported Xiaomi BLE

Total devices: 29

Brand|Name|Model|Default entities|Optional entities|S
---|---|---|---|---|---
Aqara|Door Lock N100 (Bluetooth)|[ZNMS16LM](https://home.miot-spec.com/s/1694)|*|ble|
Aqara|Door Lock N200|[ZNMS17LM](https://home.miot-spec.com/s/1695)|*|ble|
Honeywell|Smoke Alarm|[JTYJ-GD-03MI](https://home.miot-spec.com/s/2455)|*|ble|
Xiaomi|Alarm Clock|[CGD1](https://home.miot-spec.com/s/1398)|temperature, humidity, battery*|ble|
Xiaomi|Door Lock|[MJZNMS02LM](https://home.miot-spec.com/s/794)|*|ble|
Xiaomi|Door Lock|[MJZNMS03LM](https://home.miot-spec.com/s/1433)|*|ble|
Xiaomi|Door Lock|[XMZNMST02YD](https://home.miot-spec.com/s/2444)|*|ble|
Xiaomi|Door Sensor 2|[MCCGQ02HL](https://home.miot-spec.com/s/2443)|*|ble|
Xiaomi|Flower Care|[HHCCJCY01](https://home.miot-spec.com/s/152)|temperature, moisture, conductivity, illuminance, battery*|ble|
Xiaomi|Flower Pot|[HHCCPOT002](https://home.miot-spec.com/s/349)|moisture, conductivity, battery*|ble|
Xiaomi|Kettle|[YM-K1501](https://home.miot-spec.com/s/131)|power, temperature|ble|
Xiaomi|Magic Cube|[XMMF01JQD](https://home.miot-spec.com/s/1249)|action|ble|
Xiaomi|Mosquito Repellent|[WX08ZM](https://home.miot-spec.com/s/1034)|*|ble|
Xiaomi|Motion Sensor 2|[RTCGQ02LM](https://home.miot-spec.com/s/2701)|motion, illuminance, battery|ble, idle_time, action|
Xiaomi|Night Light 2|[MJYD02YL-A](https://home.miot-spec.com/s/2038)|battery, light, motion, idle_time|ble|
Xiaomi|Qingping Door Sensor|[CGH1](https://home.miot-spec.com/s/982)|*|ble|
Xiaomi|Qingping Motion Sensor|[CGPR1](https://home.miot-spec.com/s/2691)|*|ble|
Xiaomi|Qingping TH Lite|[CGDK2](https://home.miot-spec.com/s/1647)|temperature, humidity, battery*|ble|
Xiaomi|Qingping TH Sensor|[CGG1](https://home.miot-spec.com/s/839)|temperature, humidity, battery*|ble|
Xiaomi|Safe Box|[BGX-5/X1-3001](https://home.miot-spec.com/s/2480)|*|ble|
Xiaomi|TH Clock|[LYWSD02MMC](https://home.miot-spec.com/s/1115)|temperature, humidity, battery*|ble|
Xiaomi|TH Sensor|[LYWSDCGQ/01ZM](https://home.miot-spec.com/s/426)|temperature, humidity, battery*|ble|
Xiaomi|TH Sensor 2|[LYWSD03MMC](https://home.miot-spec.com/s/1371)|temperature, humidity, battery*|ble|
Xiaomi|Toothbrush T500|[MES601](https://home.miot-spec.com/s/1161)|*|ble|
Xiaomi|Viomi Kettle|[V-SK152](https://home.miot-spec.com/s/1116)|power, temperature|ble|
Xiaomi|Water Leak Sensor|[SJWS01LM](https://home.miot-spec.com/s/2147)|*|ble|
Xiaomi|ZenMeasure Clock|[MHO-C303](https://home.miot-spec.com/s/1747)|temperature, humidity, battery*|ble|
Xiaomi|ZenMeasure TH|[MHO-C401](https://home.miot-spec.com/s/903)|temperature, humidity, battery*|ble|
Yeelight|Button S1|[YLAI003](https://home.miot-spec.com/s/1983)|*|ble|

## Supported Xiaomi Mesh

Total devices: 27

Brand|Name|Model|Default entities|Optional entities|S
---|---|---|---|---|---
PTX|Mesh Double Wall Switch|[PTX-SK2M](https://home.miot-spec.com/s/2257)|left_switch, right_switch|led, left_smart, right_smart|
PTX|Mesh Downlight|[090615.light.mlig01](https://home.miot-spec.com/s/3416)|light||
PTX|Mesh Single Wall Switch|[PTX-SK1M](https://home.miot-spec.com/s/2258)|switch|led, smart|
PTX|Mesh Triple Wall Switch|[PTX-SK3M](https://home.miot-spec.com/s/3878)|left_switch, middle_switch, right_switch|led, left_smart, middle_smart, right_smart|
PTX|Mesh Triple Wall Switch|[PTX-TK3/M](https://home.miot-spec.com/s/2093)|left_switch, middle_switch, right_switch|led, left_smart, middle_smart, right_smart|
Unknown|Mesh Downlight|[lemesh.light.wy0c05](https://home.miot-spec.com/s/2351)|light||
Unknown|Mesh Downlight (RF ready)|[lemesh.light.wy0c07](https://home.miot-spec.com/s/3164)|light||
Unknown|Mesh Lightstrip (RF ready)|[crzm.light.wy0a01](https://home.miot-spec.com/s/2293)|light||
Unknown|Mesh Switch Controller|[lemesh.switch.sw0a01](https://home.miot-spec.com/s/2007)|switch||
Unknown|Mesh Wall Switch|[DHKG01ZM](https://home.miot-spec.com/s/1945)|switch|led|
Unknown|ightctl Light|[lemesh.light.wy0c08](https://home.miot-spec.com/s/3531)|light||
Xiaomi|Mesh Bulb|[MJDP09YL](https://home.miot-spec.com/s/1771)|light||
Xiaomi|Mesh Double Wall Switch|[DHKG02ZM](https://home.miot-spec.com/s/1946)|left_switch, right_switch|led, left_smart, right_smart|
Xiaomi|Mesh Double Wall Switch|[ZNKG02HL](https://home.miot-spec.com/s/2716)|left_switch, right_switch, humidity, temperature||
Xiaomi|Mesh Downlight|[MJTS01YL/MJTS003](https://home.miot-spec.com/s/1772)|light||
Xiaomi|Mesh Group|[yeelink.light.mb1grp](https://home.miot-spec.com/s/1054)|group||
Xiaomi|Mesh Single Wall Switch|[ZNKG01HL](https://home.miot-spec.com/s/2715)|switch, humidity, temperature||
Xiaomi|Mesh Triple Wall Switch|[ZNKG03HL/ISA-KG03HL](https://home.miot-spec.com/s/2717)|left_switch, middle_switch, right_switch, humidity, temperature|left_smart, middle_smart, right_smart, baby_mode|
Xiaomi|Mi Smart Electrical Outlet|[ZNCZ01ZM](https://home.miot-spec.com/s/3083)|outlet, power|led, power_protect|
XinGuang|Mesh Switch|[wainft.switch.sw0a01](https://home.miot-spec.com/s/3150)|switch||
XinGuang|Smart Light|[LIBMDA09X](https://home.miot-spec.com/s/2584)|light||
Yeelight|Mesh Bulb E14|[YLDP09YL](https://home.miot-spec.com/s/995)|light||
Yeelight|Mesh Bulb E27|[YLDP10YL](https://home.miot-spec.com/s/996)|light||
Yeelight|Mesh Bulb M2|[YLDP25YL/YLDP26YL](https://home.miot-spec.com/s/2342)|light||
Yeelight|Mesh Downlight|[YLSD01YL](https://home.miot-spec.com/s/948)|light||
Yeelight|Mesh Downlight M2|[YLTS02YL/YLTS04YL](https://home.miot-spec.com/s/2076)|light||
Yeelight|Mesh Spotlight|[YLSD04YL](https://home.miot-spec.com/s/997)|light||

<!--supported-->

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

> **Important:** Support for EFR32 chips (EZSP v8) in the zigbee2mqtt project is [experimental](https://www.zigbee2mqtt.io/guide/adapters/#experimental). At the moment they work not good and are **not recommended for use**.

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
