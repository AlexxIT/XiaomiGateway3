from dataclasses import dataclass
from typing import TYPE_CHECKING

from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    AnalogInput,
    LevelControl,
    MultistateInput,
    OnOff,
    PowerConfiguration,
    Basic,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.smartenergy import Metering

from .base import BaseConv, decode_time
from .const import BUTTON_SINGLE, BUTTON_DOUBLE, BUTTON_HOLD
from .silabs import *

if TYPE_CHECKING:
    from ..device import XDevice

assert DATA_TYPES
TYPE_BOOL = 0x10  # t.Bool
TYPE_UINT8 = 0x20  # t.uint8_t
TYPE_UINT32 = 0x23  # t.uint32_t
TYPE_ENUM8 = 0x30  # t.enum8


def conv(value: int | float, src1: int, src2: int, dst1: int, dst2: int) -> int:
    value = round((value - src1) / (src2 - src1) * (dst2 - dst1) + dst1)
    if value < min(dst1, dst2):
        value = min(dst1, dst2)
    if value > max(dst1, dst2):
        value = max(dst1, dst2)
    return value


@dataclass
class ZConverter(BaseConv):
    """Basic zigbee converter."""

    cluster_id = None  # zigbee cluster ID
    attr_id = None  # zigbee attribute ID
    ep: int = None  # zigbee endpoint number (None will decode all endpoints)
    bind: bool = None
    report: str = None

    def decode(self, device: "XDevice", payload: dict, data: dict):
        # important to check value, because reading unsupported value will return None
        if (value := data.get(self.attr_id)) is not None:
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value):
        pass

    def encode_read(self, device: "XDevice", payload: dict):
        if self.attr_id is not None:
            cmd = zcl_read(device.nwk, self.ep or 1, self.cluster_id, self.attr_id)
            payload.setdefault("commands", []).extend(cmd)

    def config(self, device: "XDevice", payload: dict):
        if self.bind:
            # noinspection PyUnresolvedReferences
            gw_ieee = device.gateways[0].ieee
            cmd = zdo_bind(
                device.nwk, self.ep or 1, self.cluster_id, device.uid[2:], gw_ieee
            )
            payload.setdefault("commands", []).extend(cmd)

        if self.report:
            mint, maxt, change = self.report.split(" ")
            cmd = zdb_report(
                device.nwk,
                self.ep or 1,
                self.cluster_id,
                self.attr_id,
                int(decode_time(mint)),
                int(decode_time(maxt)),
                int(change),
            )
            payload.setdefault("commands", []).extend(cmd)


class ZBoolConv(ZConverter):
    """Basic zigbee bool converter."""

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is not None:
            payload[self.attr] = bool(value)

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_write(
            device.nwk,
            self.ep or 1,
            self.cluster_id,
            self.attr_id,
            int(value),
            type_id=TYPE_BOOL,
        )
        payload.setdefault("commands", []).extend(cmd)


class ZMapConv(ZConverter):
    map: dict

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is not None:
            payload[self.attr] = self.map.get(value)

    def encode(self, device: "XDevice", payload: dict, value: str):
        v = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(
            device.nwk,
            self.ep or 1,
            self.cluster_id,
            self.attr_id,
            v,
            type_id=TYPE_ENUM8,
        )
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZMathConv(ZConverter):
    multiply: float = 1.0
    round: int = None

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is not None:
            if self.multiply != 1.0:
                value *= self.multiply
            if self.round is not None:
                # convert to int when round is zero
                value = round(value, self.round or None)
            payload[self.attr] = value


class ZOnOffConv(ZBoolConv):
    cluster_id = OnOff.cluster_id
    attr_id = OnOff.AttributeDefs.on_off.id

    def encode(self, device: "XDevice", payload: dict, value: bool):
        cmd = zcl_on_off(device.nwk, self.ep or 1, value)
        payload.setdefault("commands", []).extend(cmd)


class ZBrightnessConv(ZConverter):
    cluster_id = LevelControl.cluster_id
    attr_id = LevelControl.AttributeDefs.current_level.id

    def encode(self, device: "XDevice", payload: dict, value: int | float):
        transition = payload.get("transition", 0)
        cmd = zcl_level(device.nwk, self.ep or 1, round(value), transition)
        payload.setdefault("commands", []).extend(cmd)


@dataclass
class ZColorTempConv(ZConverter):
    cluster_id = Color.cluster_id
    attr_id = Color.AttributeDefs.color_temperature.id

    min: int = 153
    max: int = 500

    def encode(self, device: "XDevice", payload: dict, value: int | float):
        transition = payload.get("transition", 0)
        cmd = zcl_color_temp(device.nwk, self.ep or 1, round(value), transition)
        payload.setdefault("commands", []).extend(cmd)


class ZColorHSConv(ZConverter):
    cluster_id = Color.cluster_id
    attr_id1 = Color.AttributeDefs.current_hue.id
    attr_id2 = Color.AttributeDefs.current_saturation.id

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if self.attr_id1 in data and self.attr_id2 in data:
            hue = conv(data[self.attr_id1], 0, 254, 0, 360)
            sat = conv(data[self.attr_id2], 0, 254, 0, 100)
            payload[self.attr] = (hue, sat)

    def encode(self, device: "XDevice", payload: dict, value: tuple[int]):
        hue = conv(value[0], 0, 360, 0, 254)
        sat = conv(value[1], 0, 100, 0, 254)
        transition = payload.get("transition", 0)
        cmd = zcl_color_hs(device.nwk, self.ep or 1, hue, sat, transition)
        payload.setdefault("commands", []).extend(cmd)

    def encode_read(self, device: "XDevice", payload: dict):
        cmd = zcl_read(device.nwk, self.ep or 1, self.cluster_id, self.attr_id1)
        cmd += zcl_read(device.nwk, self.ep or 1, self.cluster_id, self.attr_id2)
        payload.setdefault("commands", []).extend(cmd)


class ZColorModeConv(ZConverter):
    cluster_id = Color.cluster_id
    attr_id = Color.AttributeDefs.color_mode.id
    map = {0: "hs", 1: "xy", 2: "color_temp"}

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is not None:
            payload[self.attr] = self.map[value]


class ZTransitionConv(BaseConv):
    def encode(self, device: "XDevice", payload: dict, value: float):
        payload[self.attr] = value


class ZVoltageConv(ZConverter):
    cluster_id = ElectricalMeasurement.cluster_id
    attr_id = ElectricalMeasurement.AttributeDefs.rms_voltage.id


@dataclass
class ZCurrentConv(ZMathConv):
    cluster_id = ElectricalMeasurement.cluster_id
    attr_id = ElectricalMeasurement.AttributeDefs.rms_current.id
    multiply: float = 0.001


class ZPowerConv(ZConverter):
    cluster_id = ElectricalMeasurement.cluster_id
    attr_id = ElectricalMeasurement.AttributeDefs.active_power.id


@dataclass
class ZEnergyConv(ZMathConv):
    cluster_id = Metering.cluster_id
    attr_id = Metering.AttributeDefs.current_summ_delivered.id
    multiply: float = 0.01


class ZOccupancyConv(ZBoolConv):
    cluster_id = OccupancySensing.cluster_id
    attr_id = OccupancySensing.AttributeDefs.occupancy.id


@dataclass
class ZOccupancyTimeoutConv(ZConverter):
    cluster_id = OccupancySensing.cluster_id
    attr_id = OccupancySensing.AttributeDefs.pir_o_to_u_delay.id

    min: int = 0
    max: int = 65535

    def encode(self, device: "XDevice", payload: dict, value: int):
        cmd = zcl_write(device.nwk, self.ep or 1, self.cluster_id, self.attr_id, value)
        payload.setdefault("commands", []).extend(cmd)
        # we need to read new value after write
        self.encode_read(device, payload)


class ZAnalogInput(ZMathConv):
    cluster_id = AnalogInput.cluster_id
    attr_id = AnalogInput.AttributeDefs.present_value.id


class ZMultistateInput(ZConverter):
    cluster_id = MultistateInput.cluster_id
    attr_id = MultistateInput.AttributeDefs.present_value.id


class ZIASZoneConv(ZConverter):
    cluster_id = IasZone.cluster_id
    command_id = IasZone.ClientCommandDefs.status_change_notification.id

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if data.get("cluster_command_id") == self.command_id:
            payload[self.attr] = (data["value"]["zone_status"] & 1) > 0

    def encode_read(self, device: "XDevice", payload: dict):
        pass


@dataclass
class ZIlluminanceConv(ZConverter):
    cluster_id = IlluminanceMeasurement.cluster_id
    attr_id = IlluminanceMeasurement.AttributeDefs.measured_value.id


@dataclass
class ZTemperatureConv(ZMathConv):
    cluster_id = TemperatureMeasurement.cluster_id
    attr_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    multiply: float = 0.01


@dataclass
class ZHumidityConv(ZMathConv):
    cluster_id = RelativeHumidity.cluster_id
    attr_id = RelativeHumidity.AttributeDefs.measured_value.id
    multiply: float = 0.01


@dataclass
class ZBatteryPercConv(ZMathConv):
    cluster_id = PowerConfiguration.cluster_id
    attr_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id


@dataclass
class ZBatteryVoltConv(ZMathConv):
    cluster_id = PowerConfiguration.cluster_id
    attr_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    multiply: float = 100


###############################################################################
# Specific defices converters
###############################################################################


class ZTuyaChildModeConv(ZBoolConv):
    cluster_id = OnOff.cluster_id
    attr_id = 0x8000


class ZTuyaLEDModeConv(ZMapConv):
    cluster_id = OnOff.cluster_id
    attr_id = 0x8001
    map = {0: "off", 1: "off/on", 2: "on/off", 3: "on"}


# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman/blob/master/src/zcl/definition/cluster.ts
# moesStartUpOnOff: {ID: 0x8002, type: DataType.enum8},
class ZTuyaPowerOnConv(ZMapConv):
    cluster_id = OnOff.cluster_id
    attr_id = 0x8002
    map = {0: "off", 1: "on", 2: "previous"}


class ZTuyaButtonModeConv(ZMapConv):
    cluster_id = OnOff.cluster_id
    attr_id = 0x8004
    map = {0: "command", 1: "event"}

    def config(self, device: "XDevice", payload: dict):
        # set default mode
        self.encode(device, payload, "event")


# Thanks to:
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/910271ae8fccb19305752d3f67381b4765853018/converters/fromZigbee.js#L4537
# https://github.com/Koenkk/zigbee-herdsman/blob/068bbe7636f588394f69f82bc25c8b68a4feada7/src/zcl/definition/cluster.ts#L4284
class ZTuyaPlugModeConv(ZMapConv):
    cluster_id = 0xE001
    attr_id = 0xD030
    map = {0: "toggle", 1: "state", 2: "momentary"}


class ZTuyaButtonConfig(ZConverter):
    def config(self, device: "XDevice", payload: dict):
        # some stupid but necessary magic from zigbee2mqtt
        for attr_id in (0x00, 0x01, 0x04, 0x05, 0x07, 0xFFFE):
            cmd = zcl_read(device.nwk, self.ep or 1, cluster_id=6, attr_id=attr_id)
        cmd += zcl_read(device.nwk, self.ep or 1, cluster_id=0xE001, attr_id=0xD011)
        payload.setdefault("commands", []).extend(cmd)


class ZTuyaButtonConv(ZConverter):
    cluster_id = OnOff.cluster_id
    attr_id = OnOff.AttributeDefs.on_off.id
    map = {0: BUTTON_SINGLE, 1: BUTTON_DOUBLE, 2: BUTTON_HOLD}

    def decode(self, device: "XDevice", payload: dict, data: dict):
        # TS004F sends click three times with same seq number
        if device.extra.get("seq") == data["seq"]:
            return

        device.extra["seq"] = data["seq"]

        try:
            payload[self.attr] = value = self.map.get(data["value"][0])
            payload["action"] = self.attr + "_" + value
        except:
            pass


# Thanks to zigbee2mqtt:
# https://github.com/Koenkk/zigbee-herdsman/blob/528b7626f2970ba87a0792920590926105a3cb48/src/zcl/definition/cluster.ts#LL460C32-L460C37
# https://github.com/Koenkk/zigbee-herdsman-converters/blob/f9115000807b21dcaa06e58c5b8e69baa4e626fe/converters/fromZigbee.js#L867
class ZPowerOnConv(ZMapConv):
    cluster_id = OnOff.cluster_id
    attr_id = 0x4003
    map = {0: "off", 1: "on", 2: "toggle", 255: "previous"}


class ZLumiCubeMain(ZConverter):
    cluster_id = MultistateInput.cluster_id
    attr_id = MultistateInput.AttributeDefs.present_value.id
    childs = {"side", "from_side", "to_side"}

    def decode(self, device: "XDevice", payload: dict, data: dict):
        # Thanks to zigbee2mqtt:
        # https://github.com/Koenkk/zigbee-herdsman-converters/blob/4a74caad6361e606e0e995d74e7f9ca2f6bdce3e/converters/fromZigbee.js#L5490
        if (value := data.get(self.attr_id)) is None:
            return
        if value == 0:
            payload["action"] = "shake"
        elif value == 2:
            payload["action"] = "wakeup"
        elif value == 3:
            payload["action"] = "fall"
        elif value & 0x200:
            payload.update({"action": "tap", "side": value & 0b111})
        elif value & 0x100:
            payload.update({"action": "slide", "side": value & 0b111})
        elif value & 0x80:
            payload.update({"action": "flip180", "side": value & 0b111})
        elif value & 0x40:
            payload.update(
                {
                    "action": "flip90",
                    "from_side": (value >> 3) & 0b111,
                    "to_side": value & 0b111,
                }
            )


class ZLumiCubeRotate(ZConverter):
    cluster_id = AnalogInput.cluster_id
    attr_id = AnalogInput.AttributeDefs.present_value.id
    childs = {"duration"}

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is None:
            return
        payload.update(
            {
                "action": "rotate",
                "angle": round(value),
                "duration": round(data[0xFF05] * 0.001, 2),
            }
        )


@dataclass
class ZLumiBasicAlarm(ZConverter):
    cluster_id = Basic.cluster_id
    basic_attr: int = None

    def decode(self, device: "XDevice", payload: dict, data: dict):
        # Some old lumi sensors doesn't sends periodic "no alarm" status.
        # But they all has this status in the heartbeats (basic cluster).
        # For "lumi.sensor_wleak.aq1" on firmware 4 sensor:
        #   100: 1 - water leak (sometimes correct, sometimes not)
        #   100: 0 - no water leak
        # For "lumi.sensor_natgas" and "lumi.sensor_smoke" sensor:
        #   150: 0x42000000 - gas
        #   150: 0x43000000 - gas and button click
        #   150: 0x08000000 - no gas button click
        #   150: 0x02040200 - smoke
        #   150: 0x03000000 - smoke and button click
        #   150: 0 - no gas, no smoke
        if value := data.get(0xFF01):
            if value[self.basic_attr] == 0:
                payload[self.attr] = False


class ZLumiSensConv(ZConverter):
    cluster_id = IasZone.cluster_id
    attr_id = 0xFFF0  # read attr
    map = {"1": "low", "2": "medium", "3": "high"}  # read_map
    write_map = {"low": 0x04010000, "medium": 0x04020000, "high": 0x04030000}

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if value := data.get(self.attr_id):
            v = hex(value)[4]  # '0x203000038010008'
            payload[self.attr] = self.map[v]

    def encode(self, device: "XDevice", payload: dict, value: str):
        cmd = zcl_write(
            device.nwk,
            self.ep or 1,
            self.cluster_id,
            0xFFF1,  # write attr
            self.write_map[value],
            type_id=TYPE_UINT32,
            mfg=0x115F,
        )
        payload.setdefault("commands", []).extend(cmd)

    def encode_read(self, device: "XDevice", payload: dict):
        if self.attr_id is not None:
            cmd = zcl_read(
                device.nwk, self.ep or 1, self.cluster_id, self.attr_id, mfg=0x115F
            )
            payload.setdefault("commands", []).extend(cmd)


class ZSonoffButtonConv(ZConverter):
    cluster_id = OnOff.cluster_id
    map = {0: "hold", 1: "double", 2: "single"}

    def decode(self, device: "XDevice", payload: dict, value: dict):
        """Conver commands to clicks."""
        command_id = value.get("cluster_command_id")
        payload[self.attr] = self.map.get(command_id)


class ZHueDimmerOnConv(ZConverter):
    cluster_id = OnOff.cluster_id

    def decode(self, device: "XDevice", payload: dict, value: dict):
        command_id = value.get("cluster_command_id")
        if command_id == 1:
            payload[self.attr] = "button_1_single"
        elif command_id == 64:
            payload[self.attr] = "button_4_single"

    def encode_read(self, device: "XDevice", payload: dict):
        pass

    def config(self, device: "XDevice", payload: dict):
        super().config(device, payload)

        # Thanks to zigbee2mqtt and ZHA (some unknown magic)
        cmd = zcl_write(device.nwk, 2, 0, 0x31, 0x0B, type_id=0x19, mfg=0x100B)
        payload.setdefault("commands", []).extend(cmd)


class ZHueDimmerLevelConv(ZConverter):
    cluster_id = LevelControl.cluster_id
    command_id = LevelControl.ServerCommandDefs.step.id

    def decode(self, device: "XDevice", payload: dict, value: dict):
        if self.command_id == value.get("cluster_command_id"):
            if value["value"]["step_mode"] == 0:
                payload[self.attr] = "button_2_single"
            elif value["value"]["step_mode"] == 1:
                payload[self.attr] = "button_3_single"

    def encode_read(self, device: "XDevice", payload: dict):
        pass


class ZLumiBrightness(BaseConv):
    """Converter decode and read data in Lumi format for support heartbeats.
    But encode data in Zigbee format for support transition.
    """

    ep = 1

    def decode(self, device: "XDevice", payload: dict, value: int):
        # lumi - 0..100, hass - 1..255
        payload[self.attr] = conv(value, 1, 100, 1, 255)

    def encode(self, device: "XDevice", payload: dict, value: int):
        if "transition" in payload:
            # noinspection PyTypeChecker
            ZBrightnessConv.encode(self, device, payload, value)
        else:
            value = conv(value, 1, 255, 1, 100)
            super().encode(device, payload, value)


@dataclass
class ZLumiColorTemp(BaseConv):
    """Converter decode and read data in Lumi format for support heartbeats.
    But encode data in Zigbee format for support transition.
    """

    minm: int = 153  # mireds (Aqara Bulb)
    maxm: int = 370  # mireds (Aqara Bulb)
    transition: float = 1.5  # default from MiHome

    def decode(self, device: "XDevice", payload: dict, value: int):
        if not isinstance(value, dict):
            payload[self.attr] = value

    def encode(self, device: "XDevice", payload: dict, value: int):
        cmd = zcl_color_temp(device.nwk, 1, value, self.transition)
        payload.setdefault("commands", []).extend(cmd)


# endpoint 2, cluster 0, attribute 51, type 0x10 (boolean)
# class ZHueLed(ZBoolConv):
#     cluster_id = Basic.cluster_id
#     attr_id = 51
#     ep = 2


# class IKEARemoteConv1(ZConverter):
#     cluster_id = OnOff.cluster_id
#
#     def decode(self, device: "XDevice", payload: dict, value: dict):
#         if value.get("command_id") == 2:
#             payload["button"] = "toggle"
#
#
# class IKEARemoteConv2(ZConverter):
#     cluster_id = LevelControl.cluster_id
#     map = {
#         1: "brightness_down_hold",
#         2: "brightness_down_click",
#         3: "brightness_down_release",
#         4: "toggle_hold",
#         5: "brightness_up_hold",
#         6: "brightness_up_click",
#         7: "brightness_up_release",
#     }
#
#     def decode(self, device: "XDevice", payload: dict, value: dict):
#         if "command_id" in value:
#             payload["button"] = self.map.get(value["command_id"])


class ZLumiOppleMode(ZConverter):
    map = {0: "binding", 1: "multiclick"}

    def encode(self, device: "XDevice", payload: dict, value: str):
        v = next(k for k, v in self.map.items() if v == value)
        cmd = zcl_write(
            device.nwk, self.ep or 1, 0xFCC0, 9, v, type_id=TYPE_UINT8, mfg=0x115F
        )
        payload.setdefault("commands", []).extend(cmd)


class ZCoverCmd(ZConverter):
    cluster_id = WindowCovering.cluster_id
    map = {
        "open": WindowCovering.ServerCommandDefs.up_open.id,
        "close": WindowCovering.ServerCommandDefs.down_close.id,
        "stop": WindowCovering.ServerCommandDefs.stop.id,
    }

    def encode(self, device: "XDevice", payload: dict, value: str):
        command_id = self.map[value]
        cmd = zcl_command(device.nwk, self.ep or 1, self.cluster_id, command_id)
        payload.setdefault("commands", []).extend(cmd)


class ZCoverPos(ZConverter):
    cluster_id = WindowCovering.cluster_id  # 258
    command_id = WindowCovering.ServerCommandDefs.go_to_lift_percentage.id
    attr_id = WindowCovering.AttributeDefs.current_position_lift_percentage.id

    def decode(self, device: "XDevice", payload: dict, data: dict):
        if (value := data.get(self.attr_id)) is not None:
            payload[self.attr] = 100 - value

    def encode(self, device: "XDevice", payload: dict, value: int):
        value = 100 - value
        cmd = zcl_command(
            device.nwk, self.ep or 1, self.cluster_id, self.command_id, int(value)
        )
        payload.setdefault("commands", []).extend(cmd)


class ZModelConv(ZConverter):
    cluster_id = Basic.cluster_id
    attr_id = Basic.AttributeDefs.model.id
