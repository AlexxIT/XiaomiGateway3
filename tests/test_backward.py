from homeassistant.const import REQUIRED_PYTHON_VER

from custom_components.xiaomi_gateway3 import *
from custom_components.xiaomi_gateway3.alarm_control_panel import *
from custom_components.xiaomi_gateway3.binary_sensor import *
from custom_components.xiaomi_gateway3.climate import *
from custom_components.xiaomi_gateway3.config_flow import *
from custom_components.xiaomi_gateway3.cover import *
from custom_components.xiaomi_gateway3.device_trigger import *
from custom_components.xiaomi_gateway3.diagnostics import *
from custom_components.xiaomi_gateway3.light import *
from custom_components.xiaomi_gateway3.number import *
from custom_components.xiaomi_gateway3.select import *
from custom_components.xiaomi_gateway3.sensor import *
from custom_components.xiaomi_gateway3.switch import *
from custom_components.xiaomi_gateway3.text import *


def test_backward():
    # https://github.com/home-assistant/core/blob/2023.2.0/homeassistant/const.py
    assert REQUIRED_PYTHON_VER >= (3, 10, 0)

    assert async_setup_entry, async_unload_entry
    assert XAlarmControlPanel
    assert XBinarySensor
    assert XAqaraS2
    assert FlowHandler
    assert XCover
    assert async_get_triggers
    assert async_get_config_entry_diagnostics
    assert XLight
    assert XNumber
    assert XSelect
    assert XSensor
    assert XSwitch
    assert XText
