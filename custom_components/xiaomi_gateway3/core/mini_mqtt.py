"""
http://stanford-clark.com/MQTT/
"""
import asyncio
import json
import random
from asyncio import StreamReader, StreamWriter
from typing import Optional

CONNECT = 1
CONNACK = 2
PUBLISH = 3
PUBACK = 4
SUBSCRIBE = 8
SUBACK = 9
PINGREQ = 12
PINGRESP = 13
DISCONNECT = 14


class MQTTMessage:
    type: int
    dup: bool
    qos: int
    retain: bool

    topic: str
    payload: bytes

    @property
    def text(self) -> str:
        return self.payload.decode()

    @property
    def json(self) -> dict:
        return json.loads(self.payload)

    def __str__(self):
        return f"{self.topic} {self.payload.decode()}"


class RawMessage:
    def __init__(self, raw=b''):
        self.pos = 0
        self.raw = raw

    @property
    def size(self):
        return len(self.raw)

    def read(self, length: int) -> bytes:
        self.pos += length
        return self.raw[self.pos - length:self.pos]

    def read_int(self, length: int) -> int:
        return int.from_bytes(self.read(length), 'big')

    def read_str(self) -> str:
        slen = self.read_int(2)
        return self.read(slen).decode()

    def read_all(self) -> bytes:
        return self.read(self.size - self.pos)

    def write_int(self, value: int, length: int):
        self.raw += value.to_bytes(length, 'big')

    def write_str(self, value: str):
        self.write_int(len(value), 2)
        self.raw += value.encode()

    def write_len(self):
        buf = b''
        var = len(self.raw)
        for _ in range(4):
            if var >= 128:
                var, b = divmod(var, 128)
                buf += (b | 128).to_bytes(1, 'big')
            else:
                buf += var.to_bytes(1, 'big')
                break
        self.raw = buf + self.raw

    def write_header(self, msg_type: int, qos=0, retain=False):
        self.write_len()
        header = (msg_type << 4) | (qos << 1) | int(retain)
        self.raw = header.to_bytes(1, 'big') + self.raw

    @staticmethod
    def read_header(header: int) -> MQTTMessage:
        msg = MQTTMessage()
        msg.type = (header >> 4) & 0b1111
        msg.dup = bool((header >> 3) & 1)
        msg.qos = (header >> 1) & 0b11
        msg.retain = bool(header & 1)
        return msg

    @staticmethod
    def connect(keep_alive: int = 0):
        msg = RawMessage()
        msg.write_str('MQIsdp')  # protocol name
        msg.write_int(3, 1)  # protocol version
        msg.write_int(0, 1)  # flags
        msg.write_int(keep_alive, 2)  # keep alive
        cid = random.randint(1000, 9999)
        msg.write_str(f"hass-{cid}")  # client ID (should be unique)
        msg.write_header(CONNECT, qos=0)
        return msg.raw

    @staticmethod
    def subscribe(msg_id: int, *topics, qos=0):
        msg = RawMessage()
        msg.write_int(msg_id, 2)  # message ID
        for topic in topics:
            msg.write_str(topic)
            msg.write_int(qos, 1)  # requested QoS
        msg.write_header(SUBSCRIBE, qos=1)
        return msg.raw

    @staticmethod
    def publish(topic: str, payload: bytes, retain=False):
        msg = RawMessage()
        msg.write_str(topic)
        # skip msg_id for QoS 0
        msg.raw += payload
        msg.write_header(PUBLISH, qos=0, retain=retain)
        return msg.raw

    @staticmethod
    def ping():
        # adds zero length after header
        return (PINGREQ << 4).to_bytes(2, 'little')

    @staticmethod
    def disconnect():
        # adds zero length after header
        return (DISCONNECT << 4).to_bytes(2, 'little')


class MiniMQTT:
    msg_id: int = None
    reader: StreamReader = None
    writer: StreamWriter = None

    def __init__(self, keepalive=15, timeout=5):
        self.keepalive = keepalive
        self.timeout = timeout

    async def read_varlen(self) -> int:
        var = 0
        for i in range(4):
            b = await self.reader.read(1)
            var += (b[0] & 0x7F) << (7 * i)
            if (b[0] & 0x80) == 0:
                break
        return var

    async def _connect(self, host: str):
        self.reader, self.writer = await asyncio.open_connection(host, 1883)

        msg = RawMessage.connect()
        self.writer.write(msg)
        await self.writer.drain()

        self.msg_id = 0

        raw = await self.reader.readexactly(4)
        assert raw[0] == CONNACK << 4
        assert raw[1] == 2
        return raw[3] == 0

    async def connect(self, host: str):
        try:
            return await asyncio.wait_for(self._connect(host), self.timeout)
        except:
            return False

    async def disconnect(self):
        msg = RawMessage.disconnect()
        self.writer.write(msg)
        await self.writer.drain()

    async def subscribe(self, topic: str):
        self.msg_id += 1
        msg = RawMessage.subscribe(self.msg_id, topic)
        self.writer.write(msg)
        await self.writer.drain()

    async def publish(self, topic: str, payload, retain=False):
        if isinstance(payload, str):
            payload = payload.encode()
        elif isinstance(payload, dict):
            payload = json.dumps(payload, separators=(',', ':')).encode()

        # no response for QoS 0
        msg = RawMessage.publish(topic, payload, retain)
        self.writer.write(msg)
        await self.writer.drain()

    async def read(self) -> Optional[MQTTMessage]:
        raw = await self.reader.read(1)
        if raw == b'':
            # disconnected
            return None

        msg = RawMessage.read_header(raw[0])
        if msg.type == PUBLISH:
            varlen = await self.read_varlen()
            raw = await self.reader.readexactly(varlen)

            pr = RawMessage(raw)
            msg.topic = pr.read_str()

            if msg.qos > 0:
                _ = pr.read_int(2)  # msg ID
                raise NotImplementedError

            msg.payload = pr.read_all()

        elif msg.type == PINGRESP:
            await self.reader.readexactly(1)

        elif msg.type == SUBACK:
            # 1b header, 1b len, 2b msgID, 1b QOS
            varlen = await self.reader.readexactly(1)
            await self.reader.readexactly(varlen[0])

        else:
            raise NotImplementedError

        return msg

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    def __aiter__(self):
        return self

    async def __anext__(self) -> MQTTMessage:
        wait_pong = False

        while True:
            try:
                msg: MQTTMessage = await asyncio.wait_for(
                    self.read(), self.keepalive
                )
                if msg is None:
                    raise StopAsyncIteration

                if msg.type == PUBLISH:
                    return msg

                if msg.type == PINGRESP:
                    wait_pong = False

            except asyncio.TimeoutError:
                if wait_pong:
                    # second ping without pong
                    raise StopAsyncIteration

                self.writer.write(RawMessage.ping())
                await self.writer.drain()

                wait_pong = True

            except Exception as e:
                raise e
