from homeassistant.components.alarm_control_panel import AlarmControlPanelEntityFeature
from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfTime,
)


def test_2022_5_0():
    assert AlarmControlPanelEntityFeature
    assert ClimateEntityFeature
    assert HVACMode
    # assert FanEntityFeature
    # assert ColorMode
    # assert LightEntityFeature


def test_2022_11_0():
    assert UnitOfEnergy
    assert UnitOfLength
    assert UnitOfPower
    assert UnitOfTemperature


def test_2023_1_0():
    assert UnitOfElectricCurrent
    assert UnitOfElectricPotential
    assert UnitOfTime
