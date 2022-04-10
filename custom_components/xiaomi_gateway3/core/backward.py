"""Backward support for older Hass versions."""
from homeassistant.const import MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION
from homeassistant.helpers.entity import Entity

# from v2021.7 important to using Entity attributes
# https://github.com/home-assistant/core/blob/933e0161501ffc160fb9009baf0112eabbae17f7/homeassistant/helpers/entity.py#L223-L238
hass_version_supported = (MAJOR_VERSION, MINOR_VERSION) >= (2021, 7)

# EntityCategory support from v2021.12
# https://github.com/home-assistant/core/blob/604a2ac3270bc51f050e0f7a7ce5079bf6da5225/homeassistant/helpers/entity.py#L183
if (MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION) >= (2021, 12):
    from homeassistant.helpers.entity import EntityCategory

    ENTITY_CATEGORY_CONFIG = EntityCategory.CONFIG
    ENTITY_CATEGORY_DIAGNOSTIC = EntityCategory.DIAGNOSTIC
else:
    ENTITY_CATEGORY_CONFIG = "config"
    ENTITY_CATEGORY_DIAGNOSTIC = "diagnostic"

# native_value support from v2021.9
# https://github.com/home-assistant/core/blob/245eec7041a2d856e1da435b686af34fee06493a/homeassistant/components/sensor/__init__.py#L161
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

        @property
        def _attr_native_unit_of_measurement(self):
            return self._attr_unit_of_measurement

        @_attr_native_unit_of_measurement.setter
        def _attr_native_unit_of_measurement(self, value):
            self._attr_unit_of_measurement = value

# EntityPlatformState support from v2022.3.3
# https://github.com/home-assistant/core/blob/737c502e948ca0fb944e4732925a3b32c9761171/homeassistant/helpers/entity.py#L211
if (MAJOR_VERSION, MINOR_VERSION, PATCH_VERSION) >= (2022, 3, "3"):
    from homeassistant.helpers.entity import EntityPlatformState


    class XEntityBase(Backward1):
        @property
        def added(self) -> bool:
            return self._platform_state == EntityPlatformState.ADDED
else:
    class XEntityBase(Backward1):
        @property
        def added(self) -> bool:
            # noinspection PyUnresolvedReferences
            return self._added
