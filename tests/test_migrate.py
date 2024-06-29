from custom_components.xiaomi_gateway3.core.const import DOMAIN
from custom_components.xiaomi_gateway3.hass.hass_utils import migrate_uid, migrate_attr


def test_migrate_uid():
    def new_identifiers(identifiers: set) -> set | None:
        assert any(i[1] != migrate_uid(i[1]) for i in identifiers if i[0] == DOMAIN)
        return {
            (DOMAIN, migrate_uid(i[1])) if i[0] == DOMAIN else i for i in identifiers
        }

    p = new_identifiers({(DOMAIN, "0x158d000fffffff")})
    assert p == {("xiaomi_gateway3", "0x00158d000fffffff")}

    p = new_identifiers({(DOMAIN, "167b9c2aea42f000")})
    assert p == {("xiaomi_gateway3", "1620060199102640128")}

    p = new_identifiers(
        {(DOMAIN, "50EC50FFFFFF"), (DOMAIN, "50ec50ffffff"), ("dummy", "id")}
    )
    assert p == {("dummy", "id"), ("xiaomi_gateway3", "50ec50ffffff")}


def test_migrate_entity_unique_id():
    def new_unique_id(unique_id: str, original_device_class: str = None):
        uid, attr = unique_id.split("_", 1)
        new_uid = migrate_uid(uid)
        new_attr = migrate_attr(attr, original_device_class)
        return f"{new_uid}_{new_attr}"

    p = new_unique_id("0x158d000fffffff_gas density")
    assert p == "0x00158d000fffffff_gas_density"

    p = new_unique_id("0x158d000fffffff_smoke density")
    assert p == "0x00158d000fffffff_smoke_density"

    p = new_unique_id("50EC50FFFFFF_light")
    assert p == "50ec50ffffff_light"

    p = new_unique_id("0x158d000fffffff_switch", "plug")
    assert p == "0x00158d000fffffff_plug"

    p = new_unique_id("167b9c2aea42f000_light")
    assert p == "1620060199102640128_light"

    p = new_unique_id("group1620060199102640128_light")
    assert p == "1620060199102640128_light"
