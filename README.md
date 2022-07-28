# Xiaomi Gateway 3 for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg)](https://github.com/hacs/integration)
[![Donate](https://img.shields.io/badge/donate-BuyMeCoffee-yellow.svg)](https://www.buymeacoffee.com/AlexxIT)
[![Donate](https://img.shields.io/badge/donate-YooMoney-8C3FFD.svg)](https://yoomoney.ru/to/41001428278477)

![](logo.png)

| Gateway | Xiaomi Mijia Smart<br>Multi-Mode Gateway | Aqara Hub E1 | Aqara Camera Hub G3 |
|---------|---|---|---|
| China model | **ZNDMWG03LM**<br>![](https://via.placeholder.com/10/00ff00/000000?text=+) supported | **ZHWG16LM**<br>![](https://via.placeholder.com/10/00ff00/000000?text=+) supported    | **ZNSXJ13LM**<br>![](https://via.placeholder.com/10/ffff00/000000?text=+) in plans |
| Euro model  | **ZNDMWG02LM**<br>![](https://via.placeholder.com/10/00ff00/000000?text=+) supported | **HE1-G01**<br> ![](https://via.placeholder.com/10/ff0000/000000?text=+) waiting hack | **CH-H03**<br>   ![](https://via.placeholder.com/10/ffff00/000000?text=+) in plans |
| Mi Home               | **yes** | **yes** | **no**  |
| Aqara Home            | **no**  | **no**  | **yes** |
| Xiaomi/Aqara Zigbee   | **yes** | **yes** |         |
| Xiaomi Bluetooth BLE  | **yes** | **no**  |         |
| Xiaomi Bluetooth Mesh | **yes** | **no**  |         |

Thanks to [@Serrj](https://community.home-assistant.io/u/serrj-sv/) for [instruction](https://community.home-assistant.io/t/xiaomi-mijia-smart-multi-mode-gateway-zndmwg03lm-support/159586/61) how to enable Telnet on old firmwares. And thanks to an unknown researcher for [instruction](https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709) how to open telnet on new firmwares.

> **Note:** Use another integrations for support:
> 
> - Xiaomi Gateway 2 (DGNWG02LM) - [external link](https://www.home-assistant.io/integrations/xiaomi_aqara/)
> - Xiaomi Gateway EU (DGNWG05LM), Aqara Hub (ZHWG11LM) - [external link](https://openlumi.github.io/)
> - Aqara G2H (ZNSXJ12LM), Aqara H1 CN (QBCZWG11LM), Aqara M1S CN (ZHWG15LM), Aqara M2 CN (ZHWG12LM), Aqara P3 CN (KTBL12LM) - [external link](https://github.com/niceboygithub/AqaraGateway)

# FAQ

**Q. Does this integration support Xiaomi Robot Vacuum, Xiaomi Philips Bulb...?**  
A. No. The integration does not support Xiaomi Wi-Fi devices.

**Q. Which Mi Home region is best to use?**  
A. Most devices are supported in the China region. In European regions may not work new Zigbee devices E1/H1/T1-series and some Mesh devices. Read more about [regional restrictions](#regional-restrictions).

**Q. What means multimode gateway beeps?**  
A. Beeps AFTER adding Zigbee devices:
1. No new devices found, the pair is stopped.
2. New device successfully added.
3. Unsupported device model.

Also, if you using hacked motion sensor - the gateway will periodically beeps. You can disable it in integration settings. 

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

**Q. Why does the two-button switch only have one entity action?**  
A. All button clicks are displayed in the status of that one entity.

# Supported Firmwares

Component support original gateway firmware. You do not need to manually open, solder and flash the devices.

#### Xiaomi Mijia Smart Multi-Mode Gateway

Maintain firmware: `v1.5.0_0102`. You **should** use [custom open telnet command](https://gist.github.com/zvldz/1bd6b21539f84339c218f9427e022709)

If you have problems with other firmware, don't even ask to fix it:

- there may be minor problems with these firmwares: v1.4.7_0XXX, v1.5.0_0026, v1.5.1_0XXX
- there can be major problems with these firmwares: v1.4.4_0XXX, v1.4.5_0XXX, v1.4.6_0XXX
- these firmwares are not supported yet: v1.5.4_0XXX

If your Mi Home doesn't offer to you new firmware - you can [update using telnet](https://github.com/zvldz/mgl03_fw/tree/main/firmware).

Component can block fw updates with **Lock Firmware** function. Mi Home app will continue to offer you update. But won't be able to install it. It should fail at 0%.

Additionally, the integration supports [custom firmware](https://github.com/zvldz/mgl03_fw/tree/main/firmware). The custom firmware works the same way as the original firmware and will not give you new features or support for new devices.

# Regional Restrictions

Device | MiHome EU | MiHome CN | Vevs EU | Vevs CN
---|---|---|---|---
Gateway 3 (CN and EU) | supported | supported | supported | supported
Zigbee old series | supported | supported | supported | supported
Zigbee E1 series (CN and EU) | no        | supported | no        | supported
Zigbee H1 and T1 series (CN and EU) | no | partially | no | some models
Bluetooth BLE and Mesh | some models | supported | supported | supported

**Xiaomi Mijia Smart Multi-Mode Gateway** has two models - `ZNDMWG03LM` (China) and `ZNDMWG02LM`/`YTC4044GL` (Euro). Both this models can be added to China or to Euro cloud servers.

**PS.** This is the ONLY Xiaomi/Aqara gateway that has the same internal model for the China and Euro versions - `lumi.gateway.mgl03`. So the Hass component and the Xiaomi cloud servers see no difference between the models.

Most **older Xiaomi/Aqara Zigbee devices** can also be added to China and to Euro cloud servers.

New **Zigbee devices from E1 series** can be added ONLY to China cloud servers. They supported in official Mi Home application.

New **Zigbee devices from H1 and T1 series** are not officially supported in Mi Home. But they can be added ONLY to China cloud servers. You can controll them from Hass (check supported list) but not from stock Mi Home application. Some of this model (mostly H1 switches and T1 relays) can be controlled from [Mi Home by Vevs](https://www.kapiba.ru/2017/11/mi-home.html).

Some of **Bluetooth BLE and Mesh** can be added ONLY to China cloud. But with [Mi Home by Vevs](https://www.kapiba.ru/2017/11/mi-home.html) they can be added to any cloud.

**PS.** You can't add **Zigbee devices E1/H1/T1** to Euro cloud even with **Mi Home by Vevs**.

If you control your devices from Home Assistant - it makes absolutely no difference which cloud they are added to. Devices are controlled locally and without delay in any case.

**PS.** Some Aqara devices are not supported at all in Mi Home in any version, e.g. **Aqara Door Lock N100 Zigbee version**.

# Supported Devices

Gateway Zigbee chip can work in three modes:

**1. Mi Home (default)**

   - Support [Xiaomi/Aqara Zigbee devices](#supported-xiaomi-zigbee) simultaneously in Mi Home and Hass
   - Support [some Zigbee devices](#supported-other-zigbee) from other brands only in Hass
   
**2. Zigbee Home Automation (ZHA)**

   - Support for [Zigbee devices of hundreds of brands](https://zigbee.blakadder.com/zha.html) only in Hass ([read more](#zigbee-home-automation-mode))

**3. Zigbee2mqtt**

   - Support for [Zigbee devices of hundreds of brands](https://www.zigbee2mqtt.io/supported-devices/) in MQTT ([read more](#zigbee2mqtt-mode))

Zigbee devices in ZHA or z2m modes doesn't controlled by this integration!

Xiaomi BLE and Mesh devices works simultaneously in Mi Home and Hass. No matter which zigbee mode is used.

Other Zigbee, BLE and Mesh devices not from the list below also may work with limited support of functionality. 

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

You can change the operation of an existing device or add support for any **Xiaomi Zigbee**, **Xiaomi BLE**, **Xiaomi Mesh** or any **other brand Zigbee** device by writing an [external converter](https://github.com/AlexxIT/XiaomiGateway3/wiki/Converters).

It is welcomed if you return a working converter to integration. You can create an issue or make a pull request.

<!--supported-->
## Supported Gateways

Total devices: 2

Brand|Name|Model|Entities|S
---|---|---|---|---
Aqara|Hub E1 CN|[ZHWG16LM](https://home.miot-spec.com/s/lumi.gateway.aqcn02)|command, data, gateway|3
Xiaomi|Gateway 3|[ZNDMWG03LM ZNDMWG02LM](https://home.miot-spec.com/s/lumi.gateway.mgl03)|alarm, command, data, cloud_link, led, gateway|4

## Supported Xiaomi Zigbee

Total devices: 82

Brand|Name|Model|Entities|S
---|---|---|---|---
Aqara|Air Quality Monitor CN|[VOCKQJK11LM](https://home.miot-spec.com/s/lumi.airmonitor.acn01)|temperature, humidity, tvoc, battery, battery_low, display_unit|
Aqara|Bulb CN|[ZNLDP12LM](https://home.miot-spec.com/s/lumi.light.aqcn02)|light, power_on_state|
Aqara|Button CN|[WXKG11LM](https://home.miot-spec.com/s/lumi.remote.b1acn01)|action, battery, battery_low, chip_temperature|
Aqara|Cube EU|[MFKZQ01LM](https://home.miot-spec.com/s/lumi.sensor_cube.aqgl01)|action, battery|5
Aqara|Curtain|[ZNCLDJ11LM](https://home.miot-spec.com/s/lumi.curtain)|motor|
Aqara|Curtain B1 EU|[ZNCLDJ12LM](https://home.miot-spec.com/s/lumi.curtain.hagl04)|motor, battery|
Aqara|Door Lock S1|[ZNMS11LM](https://home.miot-spec.com/s/lumi.lock.aq1)|square, reverse, latch, battery, key_id|
Aqara|Door Lock S2 CN|[ZNMS12LM](https://home.miot-spec.com/s/lumi.lock.acn02)|square, reverse, latch, battery, key_id|
Aqara|Door Lock S2 Pro CN|[ZNMS13LM](https://home.miot-spec.com/s/lumi.lock.acn03)|lock, square, reverse, latch, battery, action|
Aqara|Door/Window Sensor|[MCCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_magnet.aq2)|contact, battery, battery_low, chip_temperature|
Aqara|Door/Window Sensor E1 CN|[MCCGQ14LM](https://home.miot-spec.com/s/lumi.magnet.acn001)|contact, battery, battery_low|
Aqara|Double Wall Button|[WXKG02LM](https://home.miot-spec.com/s/lumi.sensor_86sw2.es1)|action, battery, battery_low, chip_temperature|
Aqara|Double Wall Button D1 CN|[WXKG07LM](https://home.miot-spec.com/s/lumi.remote.b286acn02)|action, battery, battery_low, chip_temperature|
Aqara|Double Wall Button E1 CN|[WXKG17LM](https://home.miot-spec.com/s/lumi.remote.acn004)|action, battery|
Aqara|Double Wall Button H1|[WRS-R02](https://home.miot-spec.com/s/lumi.remote.b28ac1)|action, battery, battery_low, mode|
Aqara|Double Wall Switch|[QBKG12LM](https://home.miot-spec.com/s/lumi.ctrl_ln2.aq1)|channel_1, channel_2, power, energy, action, wireless_1, wireless_2, power_on_state, led|
Aqara|Double Wall Switch (no N)|[QBKG03LM](https://home.miot-spec.com/s/lumi.ctrl_neutral2)|channel_1, channel_2, action, wireless_1, wireless_2, led|
Aqara|Double Wall Switch D1 CN (no N)|[QBKG22LM](https://home.miot-spec.com/s/lumi.switch.b2lacn02)|channel_1, channel_2, action, wireless_1, wireless_2, led|
Aqara|Double Wall Switch D1 CN (with N)|[QBKG24LM](https://home.miot-spec.com/s/lumi.switch.b2nacn02)|channel_1, channel_2, power, energy, action, wireless_1, wireless_2, power_on_state, led|
Aqara|Double Wall Switch E1 (no N)|[QBKG39LM](https://home.miot-spec.com/s/lumi.switch.b2lc04)|channel_1, channel_2, action, wireless_1, wireless_2, led, power_on_state, mode|
Aqara|Double Wall Switch E1 (with N)|[QBKG41LM](https://home.miot-spec.com/s/lumi.switch.b2nc01)|channel_1, channel_2, action, led, led_reverse, power_on_state, wireless_1, wireless_2|
Aqara|Double Wall Switch H1 CN (no N)|[QBKG28LM](https://home.miot-spec.com/s/lumi.switch.l2acn1)|channel_1, channel_2, action, led, power_on_state, wireless_1, wireless_2|
Aqara|Double Wall Switch H1 CN (with N)|[QBKG31LM](https://home.miot-spec.com/s/lumi.switch.n2acn1)|channel_1, channel_2, energy, power, action, led, led_reverse, power_on_state, wireless_1, wireless_2|
Aqara|Double Wall Switch H1 EU (no N)|[WS-EUK02](https://home.miot-spec.com/s/lumi.switch.l2aeu1)|channel_1, channel_2, action, led, power_on_state, wireless_1, wireless_2|
Aqara|Double Wall Switch H1 EU (with N)|[WS-EUK04](https://home.miot-spec.com/s/lumi.switch.n2aeu1)|channel_1, channel_2, energy, power, action, led, led_reverse, power_on_state, wireless_1, wireless_2|
Aqara|Double Wall Switch US (with N)|[WS-USC04](https://home.miot-spec.com/s/lumi.switch.b2naus01)|channel_1, channel_2, action, energy, power, led, power_on_state, wireless_1, wireless_2|
Aqara|Motion Sensor|[RTCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_motion.aq2)|motion, illuminance, battery|
Aqara|Opple Four Button CN|[WXCJKG12LM](https://home.miot-spec.com/s/lumi.remote.b486opcn01)|mode, action, battery, battery_low, chip_temperature|
Aqara|Opple MX480 CN|[XDD13LM](https://home.miot-spec.com/s/lumi.light.cwopcn03)|light|
Aqara|Opple MX650 CN|[XDD12LM](https://home.miot-spec.com/s/lumi.light.cwopcn02)|light|
Aqara|Opple Six Button CN|[WXCJKG13LM](https://home.miot-spec.com/s/lumi.remote.b686opcn01)|mode, action, battery, battery_low, chip_temperature|
Aqara|Opple Two Button CN|[WXCJKG11LM](https://home.miot-spec.com/s/lumi.remote.b286opcn01)|mode, action, battery, battery_low, chip_temperature|
Aqara|Plug EU|[SP-EUC01](https://home.miot-spec.com/s/lumi.plug.maeu01)|plug, energy, power, led, power_on_state|
Aqara|Precision Motion Sensor EU|[RTCGQ13LM](https://home.miot-spec.com/s/lumi.motion.agl04)|motion, battery, sensitivity, blind_time, battery_low, idle_time|
Aqara|Relay CN|[LLKZMK11LM](https://home.miot-spec.com/s/lumi.relay.c2acn01)|channel_1, channel_2, current, power, voltage, energy, action, chip_temperature, interlock|4
Aqara|Relay T1 CN (with N)|[DLKZMK11LM](https://home.miot-spec.com/s/lumi.switch.n0acn2)|switch, energy, power, led, power_on_state|
Aqara|Relay T1 EU (no N)|[SSM-U02](https://home.miot-spec.com/s/lumi.switch.l0agl1)|switch, chip_temperature|
Aqara|Relay T1 EU (with N)|[SSM-U01](https://home.miot-spec.com/s/lumi.switch.n0agl1)|switch, energy, power, led, power_on_state|
Aqara|Roller Shade|[ZNGZDJ11LM](https://home.miot-spec.com/s/lumi.curtain.aq2)|motor|
Aqara|Roller Shade E1 CN|[ZNJLBL01LM](https://home.miot-spec.com/s/lumi.curtain.acn002)|motor, battery, motor_reverse, battery_low, battery_voltage, battery_charging, motor_speed|
Aqara|Shake Button|[WXKG12LM](https://home.miot-spec.com/s/lumi.sensor_switch.aq3)|action, battery, battery_low, chip_temperature|
Aqara|Single Wall Button CN|[WXKG03LM](https://home.miot-spec.com/s/lumi.remote.b186acn01)|action, battery, battery_low, chip_temperature|
Aqara|Single Wall Button D1 CN|[WXKG06LM](https://home.miot-spec.com/s/lumi.remote.b186acn02)|action, battery, battery_low, chip_temperature|
Aqara|Single Wall Button E1 CN|[WXKG16LM](https://home.miot-spec.com/s/lumi.remote.acn003)|action, battery|
Aqara|Single Wall Switch|[QBKG04LM](https://home.miot-spec.com/s/lumi.ctrl_neutral1)|switch, action, wireless, led|
Aqara|Single Wall Switch|[QBKG11LM](https://home.miot-spec.com/s/lumi.ctrl_ln1.aq1)|switch, power, energy, action, wireless, led|
Aqara|Single Wall Switch D1 CN (no N)|[QBKG21LM](https://home.miot-spec.com/s/lumi.switch.b1lacn02)|switch, action, wireless, led|
Aqara|Single Wall Switch D1 CN (with N)|[QBKG23LM](https://home.miot-spec.com/s/lumi.switch.b1nacn02)|switch, power, energy, action, wireless, led|
Aqara|Single Wall Switch E1 (no N)|[QBKG38LM](https://home.miot-spec.com/s/lumi.switch.b1lc04)|switch, action, led, power_on_state, wireless, mode|
Aqara|Single Wall Switch E1 (with N)|[QBKG40LM](https://home.miot-spec.com/s/lumi.switch.b1nc01)|switch, action, led, led_reverse, power_on_state, wireless|
Aqara|Single Wall Switch H1 CN (no N)|[QBKG27LM](https://home.miot-spec.com/s/lumi.switch.l1acn1)|switch, action, led, power_on_state, wireless|
Aqara|Single Wall Switch H1 CN (with N)|[QBKG30LM](https://home.miot-spec.com/s/lumi.switch.n1acn1)|switch, energy, power, action, led, led_reverse, power_on_state, wireless|
Aqara|Single Wall Switch H1 EU (no N)|[WS-EUK01](https://home.miot-spec.com/s/lumi.switch.l1aeu1)|switch, action, led, power_on_state, wireless|
Aqara|Single Wall Switch H1 EU (with N)|[WS-EUK03](https://home.miot-spec.com/s/lumi.switch.n1aeu1)|switch, energy, power, action, led, led_reverse, power_on_state, wireless|
Aqara|TH Sensor|[WSDCGQ11LM](https://home.miot-spec.com/s/lumi.weather)|temperature, humidity, battery, pressure|
Aqara|TH Sensor T1|[WSDCGQ12LM](https://home.miot-spec.com/s/lumi.sensor_ht.agl02)|temperature, humidity, pressure, battery, battery_low|
Aqara|Thermostat S2 CN|[KTWKQ03ES](https://home.miot-spec.com/s/lumi.airrtc.tcpecn02)|climate|
Aqara|Triple Wall Switch D1 CN (no N)|[QBKG25LM](https://home.miot-spec.com/s/lumi.switch.l3acn3)|channel_1, channel_2, channel_3, action, wireless_1, wireless_2, wireless_3, power_on_state, led|
Aqara|Triple Wall Switch D1 CN (with N)|[QBKG26LM](https://home.miot-spec.com/s/lumi.switch.n3acn3)|channel_1, channel_2, channel_3, power, voltage, energy, action, wireless_1, wireless_2, wireless_3, power_on_state, led|
Aqara|Triple Wall Switch H1 CN (no N)|[QBKG29LM](https://home.miot-spec.com/s/lumi.switch.l3acn1)|channel_1, channel_2, channel_3, action, led, power_on_state, wireless_1, wireless_2, wireless_3|
Aqara|Triple Wall Switch H1 CN (with N)|[QBKG32LM](https://home.miot-spec.com/s/lumi.switch.n3acn1)|channel_1, channel_2, channel_3, energy, power, action, led, led_reverse, power_on_state, wireless_1, wireless_2, wireless_3|
Aqara|Vibration Sensor|[DJT11LM](https://home.miot-spec.com/s/lumi.vibration.aq1)|action, battery, battery_low|3
Aqara|Wall Outlet|[QBCZ11LM](https://home.miot-spec.com/s/lumi.ctrl_86plug.aq1)|outlet, power, energy, chip_temperature, power_on_state, charge_protect, led, wireless|
Aqara|Water Leak Sensor|[SJCGQ11LM](https://home.miot-spec.com/s/lumi.sensor_wleak.aq1)|moisture, battery|
Honeywell|Gas Sensor|[JTQJ-BF-01LM/BW](https://home.miot-spec.com/s/lumi.sensor_natgas)|gas_density, gas, sensitivity|4
Honeywell|Smoke Sensor|[JTYJ-GD-01LM/BW](https://home.miot-spec.com/s/lumi.sensor_smoke)|smoke_density, smoke, battery|
IKEA|Bulb E14 400 lm|[LED1536G5](https://home.miot-spec.com/s/ikea.light.led1536g5)|light|
IKEA|Bulb E14 400 lm|[LED1649C5](https://home.miot-spec.com/s/ikea.light.led1649c5)|light|
IKEA|Bulb E27 1000 lm|[LED1623G12](https://home.miot-spec.com/s/ikea.light.led1623g12)|light|
IKEA|Bulb E27 950 lm|[LED1546G12](https://home.miot-spec.com/s/ikea.light.led1546g12)|light|
IKEA|Bulb E27 980 lm|[LED1545G12](https://home.miot-spec.com/s/ikea.light.led1545g12)|light|
IKEA|Bulb GU10 400 lm|[LED1537R6](https://home.miot-spec.com/s/ikea.light.led1537r6)|light|
IKEA|Bulb GU10 400 lm|[LED1650R5](https://home.miot-spec.com/s/ikea.light.led1650r5)|light|
Xiaomi|Button|[WXKG01LM](https://home.miot-spec.com/s/lumi.sensor_switch)|action, battery, battery_low, chip_temperature|
Xiaomi|Door/Window Sensor|[MCCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_magnet)|contact, battery, battery_low, chip_temperature|
Xiaomi|Light Sensor EU|[GZCGQ01LM](https://home.miot-spec.com/s/lumi.sen_ill.mgl01)|illuminance, battery|
Xiaomi|Motion Sensor|[RTCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_motion)|motion, battery, battery_low, chip_temperature|
Xiaomi|Plug CN|[ZNCZ02LM](https://home.miot-spec.com/s/lumi.plug)|plug, power, energy, chip_temperature, power_on_state, charge_protect, led|5
Xiaomi|Plug EU|[ZNCZ04LM](https://home.miot-spec.com/s/lumi.plug.mmeu01)|plug, power, voltage, energy|
Xiaomi|Plug TW|[ZNCZ03LM](https://home.miot-spec.com/s/lumi.plug.mitw01)|plug, power, energy, chip_temperature, power_on_state, charge_protect, led|5
Xiaomi|Plug US|[ZNCZ12LM](https://home.miot-spec.com/s/lumi.plug.maus01)|plug, power, energy, chip_temperature, power_on_state, charge_protect, led|5
Xiaomi|TH Sensor|[WSDCGQ01LM](https://home.miot-spec.com/s/lumi.sensor_ht)|temperature, humidity, battery, battery_low, chip_temperature|

## Supported Other Zigbee

Total devices: 18

Brand|Name|Model|Entities|S
---|---|---|---|---
BlitzWolf|Plug|[BW-SHP13](https://www.zigbee2mqtt.io/supported-devices/#s=BW-SHP13)|plug, voltage, current, power, energy, power_on_state|5
IKEA|Bulb E27 1000 lm|[LED1623G12](https://www.zigbee2mqtt.io/supported-devices/#s=LED1623G12)|light|3
IKEA|Bulb E27 806 lm|[LED1836G9](https://www.zigbee2mqtt.io/supported-devices/#s=LED1836G9)|light|3
Ksentry Electronics|OnOff Controller|[KS-SM001](https://www.zigbee2mqtt.io/supported-devices/#s=KS-SM001)|switch|
Lonsonho|Switch w/o neutral|[TS0011](https://www.zigbee2mqtt.io/supported-devices/#s=TS0011)|switch|5
Neo|Power Plug|[NAS-WR01B](https://www.zigbee2mqtt.io/supported-devices/#s=NAS-WR01B)|plug, voltage, current, power, energy, power_on_state, led, child_mode, mode|5
Philips|Hue motion sensor|[9290012607](https://www.zigbee2mqtt.io/supported-devices/#s=9290012607)|occupancy, illuminance, temperature, battery, occupancy_timeout|4
Sonoff|Button|[SNZB-01](https://www.zigbee2mqtt.io/supported-devices/#s=SNZB-01)|action, battery|5
Sonoff|Door/Window Sensor|[SNZB-04](https://www.zigbee2mqtt.io/supported-devices/#s=SNZB-04)|contact, battery|5
Sonoff|Mini|[ZBMINI](https://www.zigbee2mqtt.io/supported-devices/#s=ZBMINI)|switch|5
Sonoff|Motion Sensor|[SNZB-03](https://www.zigbee2mqtt.io/supported-devices/#s=SNZB-03)|occupancy, battery|5
Sonoff|TH Sensor|[SNZB-02](https://www.zigbee2mqtt.io/supported-devices/#s=SNZB-02)|temperature, humidity, battery|
Tuya|Relay|[TS0001](https://www.zigbee2mqtt.io/supported-devices/#s=TS0001)|switch, power_on_state|4
Tuya|Relay|[TS0002](https://www.zigbee2mqtt.io/supported-devices/#s=TS0002)|channel_1, channel_2, power_on_state, mode|3
Tuya|Wireless Four Button|[RSH-Zigbee-SC04](https://www.zigbee2mqtt.io/supported-devices/#s=RSH-Zigbee-SC04)|action, battery, mode|
Unknown|Dimmer|[LXZ8-02A](https://www.zigbee2mqtt.io/supported-devices/#s=LXZ8-02A)|light|3
UseeLink|Power Strip|[SM-SO306E](https://www.zigbee2mqtt.io/supported-devices/#s=SM-SO306E)|channel_1, channel_2, channel_3, channel_4, usb, power_on_state|5
eWeLink|Zigbee OnOff Controller|[SA-003-Zigbee](https://www.zigbee2mqtt.io/supported-devices/#s=SA-003-Zigbee)|switch|5

## Supported Xiaomi BLE

Total devices: 33

Brand|Name|Model|Entities|S
---|---|---|---|---
Aqara|Door Lock D100|[ZNMS20LM](https://home.miot-spec.com/s/3051)|*|
Aqara|Door Lock N100 (Bluetooth)|[ZNMS16LM](https://home.miot-spec.com/s/1694)|*|
Aqara|Door Lock N200|[ZNMS17LM](https://home.miot-spec.com/s/1695)|*|
Honeywell|Smoke Alarm|[JTYJ-GD-03MI](https://home.miot-spec.com/s/2455)|action, smoke, battery|
Loock|Door Lock Classic 2X Pro|[loock.lock.cc2xpro](https://home.miot-spec.com/s/3343)|*|
Unknown|Lock M2|[ydhome.lock.m2silver](https://home.miot-spec.com/s/955)|*|
Xiaomi|Alarm Clock|[CGD1](https://home.miot-spec.com/s/1398)|temperature, humidity, battery*|
Xiaomi|Door Lock|[MJZNMS02LM](https://home.miot-spec.com/s/794)|*|
Xiaomi|Door Lock|[MJZNMS03LM](https://home.miot-spec.com/s/1433)|*|
Xiaomi|Door Lock|[XMZNMST02YD](https://home.miot-spec.com/s/2444)|*|
Xiaomi|Door/Window Sensor 2|[MCCGQ02HL](https://home.miot-spec.com/s/2443)|contact, light, battery|
Xiaomi|Flower Care|[HHCCJCY01](https://home.miot-spec.com/s/152)|temperature, moisture, conductivity, illuminance, battery*|
Xiaomi|Flower Pot|[HHCCPOT002](https://home.miot-spec.com/s/349)|moisture, conductivity, battery*|
Xiaomi|Kettle|[YM-K1501](https://home.miot-spec.com/s/131)|power, temperature|
Xiaomi|Magic Cube|[XMMF01JQD](https://home.miot-spec.com/s/1249)|action|
Xiaomi|Mosquito Repellent|[WX08ZM](https://home.miot-spec.com/s/1034)|*|
Xiaomi|Motion Sensor 2|[RTCGQ02LM](https://home.miot-spec.com/s/2701)|motion, light, battery, action, idle_time|
Xiaomi|Night Light 2|[MJYD02YL-A](https://home.miot-spec.com/s/2038)|battery, light, motion, idle_time|
Xiaomi|Qingping Door Sensor|[CGH1](https://home.miot-spec.com/s/982)|*|
Xiaomi|Qingping Motion Sensor|[CGPR1](https://home.miot-spec.com/s/2691)|motion, light, illuminance, battery, idle_time|
Xiaomi|Qingping TH Lite|[CGDK2](https://home.miot-spec.com/s/1647)|temperature, humidity, battery*|
Xiaomi|Qingping TH Sensor|[CGG1](https://home.miot-spec.com/s/839)|temperature, humidity, battery*|
Xiaomi|Safe Box|[BGX-5/X1-3001](https://home.miot-spec.com/s/2480)|*|
Xiaomi|TH Clock|[LYWSD02MMC](https://home.miot-spec.com/s/1115)|temperature, humidity, battery*|
Xiaomi|TH Sensor|[LYWSDCGQ/01ZM](https://home.miot-spec.com/s/426)|temperature, humidity, battery*|
Xiaomi|TH Sensor|[XMWSDJ04MMC](https://home.miot-spec.com/s/4611)|temperature, humidity, battery*|
Xiaomi|TH Sensor 2|[LYWSD03MMC](https://home.miot-spec.com/s/1371)|temperature, humidity, battery*|
Xiaomi|Toothbrush T500|[MES601](https://home.miot-spec.com/s/1161)|*|
Xiaomi|Viomi Kettle|[V-SK152](https://home.miot-spec.com/s/1116)|power, temperature|
Xiaomi|Water Leak Sensor|[SJWS01LM](https://home.miot-spec.com/s/2147)|water_leak, battery, action|
Xiaomi|ZenMeasure Clock|[MHO-C303](https://home.miot-spec.com/s/1747)|temperature, humidity, battery*|
Xiaomi|ZenMeasure TH|[MHO-C401](https://home.miot-spec.com/s/903)|temperature, humidity, battery*|
Yeelight|Button S1|[YLAI003](https://home.miot-spec.com/s/1983)|action, battery|

## Supported Xiaomi Mesh

Total devices: 32

Brand|Name|Model|Entities|S
---|---|---|---|---
LeMesh|Mesh Downlight|[lemesh.light.wy0c05](https://home.miot-spec.com/s/2351)|light|
LeMesh|Mesh Light|[lemesh.light.wy0c08](https://home.miot-spec.com/s/3531)|light|
LeMesh|Mesh Light (RF ready)|[lemesh.light.wy0c02](https://home.miot-spec.com/s/1910)|light|
LeMesh|Mesh Light (RF ready)|[lemesh.light.wy0c07](https://home.miot-spec.com/s/3164)|light|
PTX|Mesh Double Wall Switch|[PTX-SK2M](https://home.miot-spec.com/s/2257)|channel_1, channel_2, led, wireless_1, wireless_2|
PTX|Mesh Downlight|[090615.light.mlig01](https://home.miot-spec.com/s/3416)|light|
PTX|Mesh Single Wall Switch|[PTX-SK1M](https://home.miot-spec.com/s/2258)|switch, led, wireless|
PTX|Mesh Triple Wall Switch|[PTX-SK3M](https://home.miot-spec.com/s/3878)|channel_1, channel_2, channel_3, led, wireless_1, wireless_2, wireless_3|
PTX|Mesh Triple Wall Switch|[PTX-TK3/M](https://home.miot-spec.com/s/2093)|channel_1, channel_2, channel_3, led, wireless_1, wireless_2, wireless_3|
Unknown|Mesh Lightstrip (RF ready)|[crzm.light.wy0a01](https://home.miot-spec.com/s/2293)|light|
Unknown|Mesh Switch|[dwdz.switch.sw0a01](https://home.miot-spec.com/s/4252)|switch|
Unknown|Mesh Switch Controller|[lemesh.switch.sw0a01](https://home.miot-spec.com/s/2007)|switch|
Unknown|Mesh Switch Controller|[lemesh.switch.sw0a02](https://home.miot-spec.com/s/3169)|switch|
Unknown|Mesh Wall Switch|[DHKG01ZM](https://home.miot-spec.com/s/1945)|switch, led|
Xiaomi|Electrical Outlet|[ZNCZ01ZM](https://home.miot-spec.com/s/3083)|outlet, power, led, power_protect, power_value|
Xiaomi|Mesh Bulb|[MJDP09YL](https://home.miot-spec.com/s/1771)|light, flex_switch, power_on_state|4
Xiaomi|Mesh Double Wall Switch|[DHKG02ZM](https://home.miot-spec.com/s/1946)|channel_1, channel_2, led, wireless_1, wireless_2|
Xiaomi|Mesh Double Wall Switch|[ZNKG02HL](https://home.miot-spec.com/s/2716)|channel_1, channel_2, humidity, temperature|
Xiaomi|Mesh Downlight|[MJTS01YL/MJTS003](https://home.miot-spec.com/s/1772)|light, flex_switch, power_on_state|4
Xiaomi|Mesh Group|[yeelink.light.mb1grp](https://home.miot-spec.com/s/1054)|group|4
Xiaomi|Mesh Night Light|[MJYD05YL](https://home.miot-spec.com/s/4736)|switch, light|
Xiaomi|Mesh Single Wall Switch|[ZNKG01HL](https://home.miot-spec.com/s/2715)|switch, humidity, temperature|
Xiaomi|Mesh Triple Wall Switch|[ZNKG03HL/ISA-KG03HL](https://home.miot-spec.com/s/2717)|channel_1, channel_2, channel_3, humidity, temperature, wireless_1, wireless_2, wireless_3, baby_mode|
Xiaomi|Mosquito Repeller 2|[WX10ZM](https://home.miot-spec.com/s/4160)|switch, battery, supply, led, power_mode|
XinGuang|Mesh Switch|[wainft.switch.sw0a01](https://home.miot-spec.com/s/3150)|switch|
XinGuang|Smart Light|[LIBMDA09X](https://home.miot-spec.com/s/2584)|light|
Yeelight|Mesh Bulb E14|[YLDP09YL](https://home.miot-spec.com/s/995)|light, flex_switch, power_on_state|4
Yeelight|Mesh Bulb E27|[YLDP10YL](https://home.miot-spec.com/s/996)|light, flex_switch, power_on_state|4
Yeelight|Mesh Bulb M2|[YLDP25YL/YLDP26YL](https://home.miot-spec.com/s/2342)|light, flex_switch, power_on_state|4
Yeelight|Mesh Downlight|[YLSD01YL](https://home.miot-spec.com/s/948)|light, flex_switch, power_on_state|4
Yeelight|Mesh Downlight M2|[YLTS02YL/YLTS04YL](https://home.miot-spec.com/s/2076)|light, flex_switch, power_on_state|4
Yeelight|Mesh Spotlight|[YLSD04YL](https://home.miot-spec.com/s/997)|light, flex_switch, power_on_state|4

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

> Configuration > Integrations > Add Integration > **Xiaomi Gateway3**

If the integration is not in the list, you need to clear the browser cache.

You need to install integration two times:
1. Cloud version. It used ONLY to load tokens and names for your devices from cloud.
2. Gateway. It adds your gateway and all connected Zigbee, BLE and Mesh devices.

You may skip 1st step if you know token for you Gateway. If you have multiple Gateways - repeat step 2 for each of them.

**ATTENTION:** If you using two Hass with one gateway - you should use same integration version on both of them! 

# Network configuration 

All settings are **important** or you may have an unstable operation of the gateway.

- **Shared LAN** between Gateway and Hass server. You may use VPN, but both IP-address should be in **same network subnet**!
- **Open ping** (accept ICMP) from Gateway to Router
- **Fixed IP-address** for Gateway on your Router
- Wi-Fi Router settings:
   - **Fixed channel** from 1 to 11
   - Channel width: **20MHz** (don't use 40MHz)
   - Authentication: WPA2 (don't use WPA3)
- MikroTik Router settings:
   - Wireless > Security Profiles > Group Key Update: **01:00:00** (1 hour or more)
- Keenetic Router settings: 
   - Disable "[Airtime Fairness](https://help.keenetic.com/hc/en-us/articles/360009149400)" for 2.4GHz
   - Disable "[256-QAM](https://help.keenetic.com/hc/en-us/articles/4402854785170)" for 2.4GHz

With the following settings the operation of the gateway may be **unstable**: different subnets, closed ping to router, Wi-Fi channel 40MHz, WPA3.

# Statistics table

![](zigbee_table.png)

1. To enable stats sensors go to:

   > Configuration > Integrations > Xiaomi Gateway 3 > Options > Add statistic sensors

2. Install [Flex Table](https://github.com/custom-cards/flex-table-card) from HACS

3. Add new Lovelace tab with **Panel Mode**

4. Add new Lovelace card:
   - [example 1](https://gist.github.com/AlexxIT/120f20eef4f39071e67f698207490db9)
   - [example 2](https://github.com/avbor/HomeAssistantConfig/blob/master/lovelace/views/vi_radio_quality_gw3.yaml)

**Gateway binary sensor**

- sensor shows connection to gateway, so you can check the stability of your Wi-Fi
- **bluetooth_tx/_rx** - amount of bytes read and transmitted via BT serial port
- **bluetooth_oe** - amount of errors when reading data via BT serial port
- **zigbee_tx/_rx/_oe** - same for zigbee serial port
- **radio_tx_power** - zigbee chip power
- **radio_channel** - zigbee chip channel
- **free_mem** - gateway free memory in bytes
- **load_avg** - gateway CPU `/proc/loadavg`
- **rssi** - gateway Wi-Fi signal strength
- **uptime** - gateway uptime after reboot

**Zigbee sensor**

- sensor shows time of receiving the last message from this device
- **ieee** - zigbee device "long" address
- **nwk** - zigbee device "short" address
- **available** - device available state
- **parent** - `0xABCD` if device connected to zigbee router or `-` if device connected to gateway or `?` for unknown parent 
- **type** - zigbee `router` or end `device` or `?` for unknown type
- **msg_received** - amount of messages received from the device
- **msg_missed** - amount of unreceived messages from the device, calculated using the sequence number of messages
- **linkquality** - zigbee signal quality, below 100 is very weak
- **rssi** - zigbee signal quality, no recommendations
- **last_msg** - type of last received message
- **new_resets** - the number of device reboots since Hass reboot, supported in some Xiaomi/Aqara devices

**BLE and Mesh sensor**

- sensor shows time of receiving the last message from this device
- **mac** - device MAC address
- **available** - device available state
- **msg_received** - amount of messages received from the device
- **last_msg** - type of last received message

# Gateway controls

The old version of integration used two switches, pair and firmware_lock. If you still have them after the upgrade, remove them manually.

The new version has two drop-down lists (select entities) - command and data.

Available commands:

- **Idle** - reset the command select to the default state
- **Zigbee Pair** - start the process of adding a new zigbee device
   - you can also start the process by pressing the physical button on the gateway three times
   - you can also start the process from the Mi Home app
- **Zigbee Bind** - configure the bindings of zigbee devices, only if they support it
- **Zigbee OTA** - try to update the zigbee device if there is firmware for it
- **Zigbee Config** - start the initial setup process for the device
   - the battery devices must first be woken up manually
- **Zigbee Remove** - start the zigbee device removal process
- **Zigbee Table Update** - update the zigbee stats table manually
- **Firmware Lock** - block the gateway firmware update ([read more](#supported-firmwares))
- **Gateway Reboot** - reboot gateway
- **Gateway Enable FTP** - enable FTP on gateway
- **Gateway Dump Data** - save all gateway data in the Hass configuration folder

# Advanced config

## Integration config

> Configuration > Integrations > Xiaomi Gateway 3 > CONFIGURE

- **Host** - gateway IP-address, should be fixed on your Wi-Fi router
- **Token** - gateway Mi Home token, changed only when you add gateway to Mi Home app
- **Open Telnet command** - read [supported firmwares](#supported-firmwares) section
- **Support Bluetooth devices** - enable processing BLE and Mesh devices data from gateway
- **Add statistic sensors** - [read more](#statistics-table)
- **Debug logs** - enable different levels of logging

Don't enable DANGER settings if you don't know what you doing.

**[DANGER] Disable buzzer**

Mute the gateway when the user presses the button on the zigbee device. The same sound is made by the gateway for [Aqara Motion Sensor Hack for 5 sec](https://community.home-assistant.io/t/aqara-motion-sensor-hack-for-5-sec/147959). This is dangerous because you must remember that you will lose confirmation beep for all zigbee devices on the gateway.

**[DANGER] Use storage in memory**

Multi-Mode Gateway has an hardware problem with interruptions for zigbee and bluetooth serial data. You can lose zigbee or bluetooth data when writing to the gateway permanent memory. This setting reduces the amount of writing to the gateway's permanent memory. But if you restart the gateway at an bad moment - you may lose the newly added devices and have to add them again.

**[DANGER] Mode ZHA or zigbee2mqtt**

This setting switches the zigbee chip into ZHA or zigbee2mqtt support mode. When the setting is changed, a different version of firmware is flashed into the zigbee chip. All Zigbee devices stop working with Mi Home app.

**Attention!** This mode is retained even when the integration is removed or when the gateway is rebooted or reset. When reinstalling integration, the mode may be displayed as off, although it may actually be on. If you are not sure what mode is on - turn the setting on, wait for it to turn on without errors, and then turn it off and wait for it to turn off without errors.

## Devices config

This options configured in the `configuration.yaml`. Section: `xiaomi_gateway3 > devices > IEEE or MAC`.

As a device you can specify:

- IEEE - should be 18 symbols with `0x` and leading zeroes (for zigbee devices)
- MAC - should be 12 symbols (for BLE and Mesh devices)
- model - string for zigbee devices and number for BLE and Mesh devices
- type - gateway, zigbee, ble, mesh

**Overwrite device model**

This is useful if:

- you have unsupported device with exact same functionality as supported device, example:
   - for simple relay use model: `01MINIZB`
   - for bulb with brightness use model: `TRADFRI bulb E27 W opal 1000lm`
   - for bulb with color temp use model: `TRADFRI bulb E14 WS opal 600lm`
- you have Sonoff device with wrong firmware ([example](https://github.com/Koenkk/zigbee-herdsman-converters/issues/1449))
- you have Tuya device with same model for many different devices
- you want to use external converters only for one device

```yaml
xiaomi_gateway3:
  devices:
    "0x00158d0001d82999":  # match device by IEEE or MAC
      model: 01MINIZB
```

**Change switch to light**

Depending on the model of the device, your entity may be called: `switch`, `plug`, `outlet`, `channel_1`, etc.

```yaml
xiaomi_gateway3:
  devices:
    "0x00158d0001d82999":  # match device by IEEE or MAC
      entities:
        channel_1: light   # change entity domain (switch to light)
```

**Create sensors from attributes**

```yaml
xiaomi_gateway3:
  devices:
    "lumi.sensor_motion.aq2":  # match device by model
      entities:
        zigbee: sensor         # adds stat entity only for this device
        parent: sensor         # adds entity from attribute value
        linkquality: sensor    # adds entity from attribute value
```

**Change device or entity name**

Attention! You can change device name, entity name and entity_id safely from GUI. But if you want, you can change the device name and the entity_id part of the YAML.

```yaml
xiaomi_gateway3:
  devices:
    "0x00158d0001d82999":  # match device by IEEE or MAC
      name: Kitchen Refrigerator         # overwrite device name
      entity_name: kitchen_refrigerator  # overwrite entity_id part
```

**Additional attributes for entities**

Useful if you want to:

- put additional data in the [statistics table](#statistics-table)
- collect entities data in scripts and automations

Attention! Template is calculated only at the start of the Hass.

```yaml
xiaomi_gateway3:
  attributes_template: |
    {% if attr in ('zigbee', 'ble', 'mesh') %}{{{
      "device_name": device.info.name,
      "device_fw_ver": device.fw_ver,
      "device_model": device.model,
      "device_market_model": device.info.model,
      "gateway_name": gateway.info.name,
      "gateway_fw_ver": gateway.fw_ver
    }}}{% elif attr == 'gateway' %}{{{
      "device_fw_ver": device.fw_ver,
    }}}{% endif %}
```

## Entities customize

This options configured in the `configuration.yaml`. Section: `homeassistant > customize > entity_id`.

**Occupancy timeout** for moving sensor.

![](occupancy_timeout.png)

- a **simple timer** starts every time a person moves
- the **progressive timer** starts with a new value with each new movement of the person, the more you move - the longer the timer
- **fast back timer** starts with doubled value if the person moves immediately after the timer is off

```yaml
homeassistant:
  customize:
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
homeassistant:
  customize:
    binary_sensor.0x158d0003456789_contact:
      invert_state: 1  # any non-empty value will reverse the logic
```

**Ignore offline** device status.

```yaml
homeassistant:
  customize:
    switch.0x158d0003456789_switch:
      ignore_offline: 1  # any non-empty value
```

**Zigbee bulb default transition**.

```yaml
homeassistant:
  customize:
    light.0x86bd7fffe000000_light:
      default_transition: 5
```

# Zigbee Home Automation Mode

**Supported only for Multi-Mode Gateway.**

You **do not need** to solder or flash the gate. It is ready to work with the ZHA out of the box.

> **Note:** ZHA developers [do not recommend](https://github.com/zigpy/bellows#hardware-requirement) using ZHA with EZSP radios for WiFi-based bridges because of possible stability problems. But a range of users use the gate in this mode without issues.

**Video DEMO**

[![Zigbee Home Automation (ZHA) with Xiaomi Gateway 3 on original firmware without soldering](https://img.youtube.com/vi/AEkiUK7wGbs/mqdefault.jpg)](https://www.youtube.com/watch?v=AEkiUK7wGbs)

[Zigbee Home Automation](https://www.home-assistant.io/integrations/zha/) (ZHA) is a standard Home Assistant component for managing Zigbee devices. It works with various radio modules such as CC2531, Conbee II, Tasmoted Sonoff ZBBridge and others.

**Attention: ZHA mode cannot work simultaneously with Mi Home!**

When you turn on ZHA mode - zigbee devices in Mi Home will stop working. Bluetooth devices (BLE and Mesh) will continue to work in Mi Home and Hass.

To switch the mode go to:

> Configuration > Integrations > Xiaomi Gateway 3 > Options > Mode

Zigbee devices will not migrate from Mi Home to ZHA. You will need to pair them again with ZHA.

You can change the operating mode at any time. This mode will flash firmware of Gateway Zigbee chip to a new version with reduced speed, to avoid errors in the data. And flash it back when you switch back to Mi Home mode. Switch back before any Gateway firmware updates via Mi Home.

Thanks to [@zvldz](https://github.com/zvldz) for help with [socat](http://www.dest-unreach.org/socat/).

# Zigbee2MQTT Mode

> **Important:** The zigbee chip of this gateway (EFR32 EZSP v8) is supported in zigbee2mqtt in [experimental mode](https://www.zigbee2mqtt.io/guide/adapters/#experimental).

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

# Multiple Hass

It's safe to use multiple Hass servers (main and reserve) with integration, but:

- You should use the same integration version and same integration settings on both servers
- You may use different Hass versions on both servers
- If you using ZHA mode:
   - ZHA integration should be installed only on one Hass
   - Gateway integration may be installed only on one Hass or on both, but with same integration version and same integration settings

# Disable Buzzer

This option disable only beeps from hacked motion sensor (5 sec):

> Configuration > Integrations > Xiaomi Gateway 3 > Options > Disable buzzer

# How it works

The component enables **Telnet** on Gateway via [Miio protocol](https://github.com/rytilahti/python-miio).

The component starts the **MQTT Server** on the public port of the Gateway. All the Zigbee logic in the Gateway runs on top of the built-in MQTT Server. By default, access to it is closed from the outside.

**ATTENTION:** Telnet and MQTT work without a password! Do not use this method on public networks.

After rebooting the device, all changes will be reset. The component will launch Telnet and public MQTT every time it detects that they are disabled.

# Troubleshooting

### Can't connect to gateway

- Check [network config](#network-configuration) readme section
- Check if the Gateway really has the IP-address you set in the configuration
- Check if the Gateway really use the MiHome token you set in the configuration. When you add a hub to MiHome - its token changes. The integration only updates tokens when Hass starts. And only if there are no problems with connection to the cloud servers. If there are problems, the old (wrong) token value will be shown.

### Lost connection with Zigbee and Bluetooth devices

- Check [network config](#network-configuration) readme section, gateway and Wi-Fi router settings must be fully matched to all items in the section
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
