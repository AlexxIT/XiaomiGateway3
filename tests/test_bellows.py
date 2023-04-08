from bellows.uart import Gateway


def test_xxx():
    class FakeTransport:
        calls = []

        def frame_received(self, data):
            self.calls.append(("frame_received", data))

        def write(self, data):
            self.calls.append(("write", data))

    fake = FakeTransport()

    uart = Gateway(fake)
    uart.connection_made(fake)

    uart.data_received(bytes.fromhex("45"))
    uart.data_received(bytes.fromhex("41a157"))
    uart.data_received(bytes.fromhex("547915ac"))
    uart.data_received(bytes.fromhex("4d7e"))

    assert fake.calls
