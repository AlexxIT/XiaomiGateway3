"""If seq is the same in a short time, the device will not respond.
Increment seq by 100 won't help, because seq may still be the same.
"""

import random

import miio
from miio.miioprotocol import MiIOProtocol


class MiIOProtocolFix(MiIOProtocol):
    discovered = False
    seq = -1

    @property
    def _discovered(self):
        return self.discovered

    @_discovered.setter
    def _discovered(self, value: bool):
        self.discovered = value

        if not value:
            self.seq = random.randint(0, 999999)

    @property
    def _id(self) -> int:
        self.seq += 1
        if self.seq >= 999999:
            self.seq = 1
        return self.seq


class Device(miio.Device):
    # noinspection PyMissingConstructor
    def __init__(self, ip: str, token: str):
        self._protocol = MiIOProtocolFix(ip, token)

    def get_device_list(self) -> list:
        devices = {}

        for _ in range(16):
            # load only 8 device per part
            part = self.send('get_device_list')
            if len(part) == 0:
                return []

            for item in part:
                devices[item['num']] = item

        return list(devices.values())

    def get_device_prop(self, did: str, params: dict) -> dict:
        if did.startswith('lumi.'):
            values = self.send('get_device_prop', [did] + list(params.keys()))
            names = params.values()
            return dict(zip(names, values))

        else:
            # [{'code': 0, 'did': '123', 'piid': 1, 'siid': 3, 'value': 123}]
            values = self.send('get_properties', [
                {'did': did, 'siid': int(p[0]), 'piid': int(p[2])}
                for p in params.keys()
            ])
            return {
                params[f"{p['siid']}.{p['piid']}"]: p['value']
                for p in values
            }
