"""Backward support for older Hass versions."""
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION
from homeassistant.helpers.entity import Entity

# from v2021.7 important to using Entity attributes
# https://github.com/home-assistant/core/blob/933e0161501ffc160fb9009baf0112eabbae17f7/homeassistant/helpers/entity.py#L223-L238
hass_version_supported = (MAJOR_VERSION, MINOR_VERSION) >= (2021, 7)

if (MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION) >= (2021, 12):
    from homeassistant.helpers.entity import EntityCategory

    ENTITY_CATEGORY_CONFIG = EntityCategory.CONFIG
    ENTITY_CATEGORY_DIAGNOSTIC = EntityCategory.DIAGNOSTIC
else:
    ENTITY_CATEGORY_CONFIG = "config"
    ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"

if (MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION) >= (2021, 9):
    Backward1 = Entity
else:
    class Backward1(Entity):
        @property
        def _attr_native_value(self):
            return self._attr_state

        @_attr_native_value.setter
        def _attr_native_value(self, value):
            self._attr_state = value

if (MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION) >= (2022, 3, "3"):
    from homeassistant.helpers.entity import EntityPlatformState


    class Backward2(Backward1):
        @property
        def added(self) -> bool:
            return self._platform_state == EntityPlatformState.ADDED
else:
    class Backward2(Backward1):
        @property
        def added(self) -> bool:
            # noinspection PyUnresolvedReferences
            return self._added

if (MAJOR_VERSION, MINOR_VERSION) >= (2022, 4):
    XEntityBase = Backward2
else:
    class XEntityBase(Backward2):
        @property
        def _attr_native_unit_of_measurement(self):
            return self._attr_unit_of_measurement

        @_attr_native_unit_of_measurement.setter
        def _attr_native_unit_of_measurement(self, value):
            self._attr_unit_of_measurement = value
