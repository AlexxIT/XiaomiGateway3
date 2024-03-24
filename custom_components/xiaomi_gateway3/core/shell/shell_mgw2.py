from .shell_e1 import ShellE1
from ..unqlite import SQLite


class ShellMGW2(ShellE1):
    db: SQLite = None

    async def read_db_bluetooth(self) -> SQLite:
        if not self.db:
            raw = await self.read_file(
                "/data/local/miio_bt/mible_local.db", as_base64=True
            )
            self.db = SQLite(raw)
        return self.db

    async def read_silabs_devices(self) -> bytes:
        return await self.read_file("/data/zigbee_host/devices.txt")
