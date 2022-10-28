import base64

from .shell_arm import ShellARM

TAR_DATA = "tar -czOC /data mha_master miio storage zigbee devices.txt gatewayInfoJson.info 2>/dev/null | base64"


# noinspection PyAbstractClass
class ShellE1(ShellARM):
    model = "e1"

    async def tar_data(self):
        raw = await self.exec(TAR_DATA, as_bytes=True)
        return base64.b64decode(raw)
