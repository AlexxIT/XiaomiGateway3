"""Synthetic recovery tests. No gateway or Home Assistant instance is contacted."""

import asyncio
import base64
import importlib.util
import io
import json
import os
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest
from aiohttp import ClientSession
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "recovery_cli", ROOT / "scripts/recover_gateway_key.py"
)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
core = cli.load_core()
IDENTITY = core.GatewayIdentity(
    "lumi.gateway.mgl001", "1.0.8_0013", "00:11:22:33:44:55"
)
FIXTURE_KEY = "fixture-key-1234"


@pytest.fixture(autouse=True)
def local_receiver_sockets():
    """Permit loopback fixtures when HA's test plugin blocks sockets."""
    try:
        import pytest_socket
    except ImportError:
        yield
        return
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["127.0.0.1", "::1"], allow_unix_socket=True)
    try:
        yield
    finally:
        pytest_socket.disable_socket(allow_unix_socket=True)


def encrypt_config(
    key, iv, *, content=None, name="device.conf", extra=False, link=False
):
    if content is None:
        content = f"model={IDENTITY.model}\nmac={IDENTITY.mac}\nkey={FIXTURE_KEY}\n"
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w", format=tarfile.USTAR_FORMAT) as archive:
        member = tarfile.TarInfo(name)
        if link:
            member.type = tarfile.SYMTYPE
            member.linkname = "/etc/passwd"
        else:
            member.size = len(content.encode())
        archive.addfile(member, None if link else io.BytesIO(content.encode()))
        if extra:
            member = tarfile.TarInfo("other.conf")
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))
    padder = padding.PKCS7(128).padder()
    padded = padder.update(stream.getvalue()) + padder.finalize()
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv)).encryptor()
    return encryptor.update(padded) + encryptor.finalize()


def test_identity_and_profile_boundaries():
    assert core.supports_recovery(IDENTITY)
    assert not core.supports_recovery(
        core.GatewayIdentity(IDENTITY.model, "1.0.8_0015", IDENTITY.mac)
    )
    assert not core.supports_recovery(
        core.GatewayIdentity("lumi.gateway.mcn001", IDENTITY.firmware, IDENTITY.mac),
        True,
    )
    assert core.normalise_mac("001122334455") == IDENTITY.mac
    for value in ("0.0.0.0", "127.0.0.1", "8.8.8.8", "host.local", "::1", "100.64.0.1"):
        with pytest.raises(core.RecoveryError, match="invalid_input"):
            core.private_ipv4(value)
    assert core.private_ipv4("192.168.100.2") == "192.168.100.2"


@pytest.mark.parametrize(
    "options",
    [
        {"name": "../device.conf"},
        {"name": "/device.conf"},
        {"extra": True},
        {"link": True},
        {"content": "model=wrong\nmac=00:11:22:33:44:55\nkey=fixture-key-1234\n"},
        {
            "content": "model=lumi.gateway.mgl001\nmac=00:11:22:33:44:66\nkey=fixture-key-1234\n"
        },
        {"content": "model=lumi.gateway.mgl001\nmac=00:11:22:33:44:55\nkey=short\n"},
        {
            "content": "model=lumi.gateway.mgl001\nmac=00:11:22:33:44:55\nkey=fixture-key-1234\nkey=fixture-key-1234\n"
        },
        {"content": "x" * (core.MAX_CONFIG + 1)},
    ],
)
def test_archive_refusals(options):
    key, iv = bytes(range(16)), bytes(range(16, 32))
    encrypted = encrypt_config(key, iv, **options)
    with pytest.raises(core.RecoveryError, match="invalid_upload"):
        core.read_gateway_key(encrypted, key, iv, IDENTITY)


def test_valid_archive_and_invalid_ciphertext():
    key, iv = bytes(range(16)), bytes(range(16, 32))
    encrypted = encrypt_config(key, iv)
    assert core.read_gateway_key(encrypted, key, iv, IDENTITY) == FIXTURE_KEY
    for invalid in (b"", encrypted[:-1], b"x" * 16, b"x" * (core.MAX_UPLOAD + 16)):
        with pytest.raises(core.RecoveryError, match="invalid_upload"):
            core.read_gateway_key(invalid, key, iv, IDENTITY)


def test_receiver_authentication_bounds_and_duplicate():
    async def run():
        receiver = core.KeyReceiver("127.0.0.1", "127.0.0.1", 0, IDENTITY)
        try:
            await receiver.start()
            assert (
                len(receiver.params["encryptKey"]) == len(receiver.params["iv"]) == 24
            )
            async with ClientSession() as session:
                async with session.put(receiver.url + "bad", data=b"x") as response:
                    assert response.status == 404
                receiver.host = "127.0.0.2"
                async with session.put(receiver.url, data=b"x") as response:
                    assert response.status == 403
                receiver.host = "127.0.0.1"
                async with session.put(
                    receiver.url,
                    data=b"x",
                    headers={"Content-Length": str(core.MAX_UPLOAD + 1)},
                ) as response:
                    assert response.status == 413
                assert not receiver.future.done()
                encrypted = encrypt_config(receiver.key, receiver.iv)
                async with session.put(receiver.url, data=encrypted) as response:
                    assert response.status == 200
                assert await receiver.future == FIXTURE_KEY
                async with session.put(receiver.url, data=encrypted) as response:
                    assert response.status == 409
        finally:
            await receiver.close()
        assert not receiver.runner.sites

    asyncio.run(run())


def test_receiver_invalid_upload():
    async def run():
        receiver = core.KeyReceiver("127.0.0.1", "127.0.0.1", 0, IDENTITY)
        try:
            await receiver.start()
            async with ClientSession() as session, session.put(
                receiver.url, data=b"x"
            ) as response:
                assert response.status == 400
            with pytest.raises(core.RecoveryError, match="invalid_upload"):
                await receiver.future
        finally:
            await receiver.close()

    asyncio.run(run())


@pytest.mark.parametrize("ack", [{"result": ["ok"]}, {}, None])
def test_end_to_end_synthetic_upload_and_lost_ack(monkeypatch, ack):
    async def probe(*args):
        return IDENTITY

    class FakeMiIO:
        def __init__(self, *args):
            pass

        async def send(self, method, params, tries):
            assert method == "async_device_feedback_log" and tries == 1
            assert (
                params["fileList"] == params["filelist"] == ["/data/miio/device.conf"]
            )
            encrypted = encrypt_config(
                base64.urlsafe_b64decode(params["encryptKey"]),
                base64.urlsafe_b64decode(params["iv"]),
            )
            async with ClientSession() as session, session.put(
                params["url"], data=encrypted
            ) as response:
                assert response.status == 200
            return ack

    monkeypatch.setattr(core, "async_probe_gateway", probe)
    monkeypatch.setattr(core, "AsyncMiIO", FakeMiIO)
    monkeypatch.setattr(core, "private_ipv4", lambda address: address)
    assert (
        asyncio.run(core.async_recover_gateway_key("127.0.0.1", "0" * 32, "127.0.0.1"))
        == FIXTURE_KEY
    )


@pytest.mark.parametrize(
    "response,expected",
    [
        ({"error": {"code": -1}}, "method_rejected"),
        ({"result": {"code": -4004}}, "method_rejected"),
        ({"result": ["ok"]}, "upload_timeout"),
    ],
)
def test_rejection_and_ack_without_upload(monkeypatch, response, expected):
    async def probe(*args):
        return IDENTITY

    class FakeMiIO:
        def __init__(self, *args):
            pass

        async def send(self, *args, **kwargs):
            return response

    monkeypatch.setattr(core, "async_probe_gateway", probe)
    monkeypatch.setattr(core, "AsyncMiIO", FakeMiIO)
    monkeypatch.setattr(core, "private_ipv4", lambda address: address)
    with pytest.raises(core.RecoveryError, match=expected):
        asyncio.run(
            core.async_recover_gateway_key(
                "127.0.0.1", "0" * 32, "127.0.0.1", timeout=1
            )
        )


def test_cancellation_closes_receiver(monkeypatch):
    async def probe(*args):
        return IDENTITY

    receivers = []

    class Receiver(core.KeyReceiver):
        async def start(self):
            await super().start()
            receivers.append(self)

    class FakeMiIO:
        def __init__(self, *args):
            pass

        async def send(self, *args, **kwargs):
            return {}

    monkeypatch.setattr(core, "async_probe_gateway", probe)
    monkeypatch.setattr(core, "AsyncMiIO", FakeMiIO)
    monkeypatch.setattr(core, "KeyReceiver", Receiver)
    monkeypatch.setattr(core, "private_ipv4", lambda address: address)

    async def run():
        task = asyncio.create_task(
            core.async_recover_gateway_key("127.0.0.1", "0" * 32, "127.0.0.1")
        )
        for _ in range(100):
            if receivers:
                break
            await asyncio.sleep(0.01)
        assert receivers
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert not receivers[0].runner.sites
        assert receivers[0].future.cancelled()

    asyncio.run(run())


@pytest.mark.parametrize(
    "device_id,error", [(None, "cannot_connect"), (1, "invalid_token")]
)
def test_probe_transport_failures(monkeypatch, device_id, error):
    class FakeMiIO:
        def __init__(self, *args):
            self.device_id = device_id

        async def info(self, **kwargs):
            return None

    monkeypatch.setattr(core, "AsyncMiIO", FakeMiIO)
    with pytest.raises(core.RecoveryError, match=error):
        asyncio.run(core.async_probe_gateway("192.168.100.2", "0" * 32))


def test_script_private_file_and_no_overwrite(tmp_path):
    tmp_path.chmod(0o700)
    token = tmp_path / "token"
    token.write_text("0" * 32)
    token.chmod(0o600)
    assert cli.read_private_token(token) == "0" * 32
    token.chmod(0o644)
    with pytest.raises(ValueError):
        cli.read_private_token(token)
    target = tmp_path / "key.json"
    fd = cli.reserve_output(target)
    os.close(fd)
    assert target.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        cli.reserve_output(target)
    tmp_path.chmod(0o755)
    fd = cli.reserve_output(tmp_path / "other")
    os.close(fd)
    assert (tmp_path / "other").stat().st_mode & 0o777 == 0o600


def test_cli_success_and_failure_cleanup(tmp_path, capsys):
    tmp_path.chmod(0o700)
    token = tmp_path / "token"
    token.write_text("0" * 32)
    token.chmod(0o600)

    class FakeCore:
        async def async_probe_gateway(self, *args):
            return IDENTITY

        async def async_recover_gateway_key(self, *args, **kwargs):
            return FIXTURE_KEY

    args = SimpleNamespace(
        token_file=token,
        output=tmp_path / "key.json",
        hub="192.168.100.2",
        callback_address=None,
        timeout=90,
        port=0,
        experimental=False,
    )
    asyncio.run(cli.recover(args, FakeCore()))
    assert json.loads(args.output.read_text())["key"] == FIXTURE_KEY
    assert f"Gateway key: {FIXTURE_KEY}" in capsys.readouterr().out

    class BadCore(FakeCore):
        async def async_recover_gateway_key(self, *args, **kwargs):
            raise core.RecoveryError("upload_timeout")

    args.output = tmp_path / "failed.json"
    with pytest.raises(core.RecoveryError):
        asyncio.run(cli.recover(args, BadCore()))
    assert not args.output.exists()


def test_sensitive_miio_log_parameters_are_redacted():
    transport = __import__(core.__package__ + ".mini_miio", fromlist=["_log_params"])
    for method in ("async_device_feedback_log", "system_command"):
        assert (
            transport._log_params(
                method, {"password": "private", "encryptKey": "private"}
            )
            == "[redacted]"
        )
    assert transport._log_params("miIO.info", []) == []


@pytest.mark.parametrize("save_file", [False, True])
def test_script_prompts_for_token_and_prints_key(tmp_path, monkeypatch, capsys, save_file):
    import getpass
    prompts = []

    def pasted_token(prompt):
        prompts.append(prompt)
        return "0" * 32

    monkeypatch.setattr(getpass, "getpass", pasted_token)

    class FakeCore:
        async def async_probe_gateway(self, host, token):
            assert host == "192.168.100.2"
            assert token == "0" * 32
            return IDENTITY

        async def async_recover_gateway_key(self, *args, **kwargs):
            return FIXTURE_KEY

    tmp_path.chmod(0o755)
    output = tmp_path / "key.json" if save_file else None
    args = SimpleNamespace(token_file=None, output=output, hub="192.168.100.2",
                           callback_address=None, timeout=90, port=0)
    asyncio.run(cli.recover(args, FakeCore()))
    text = capsys.readouterr().out
    assert f"Gateway key: {FIXTURE_KEY}" in text
    assert "0" * 32 not in text
    assert prompts == ["Mi Home token: "]
    if save_file:
        assert json.loads(output.read_text())["key"] == FIXTURE_KEY
        assert output.stat().st_mode & 0o777 == 0o600
    else:
        assert not list(tmp_path.iterdir())


def test_script_default_run_prompts_for_host(monkeypatch):
    from unittest.mock import AsyncMock
    monkeypatch.setattr("builtins.input", lambda prompt: " 192.168.100.2 ")
    monkeypatch.setattr(cli, "load_core", lambda: object())
    recover = AsyncMock()
    monkeypatch.setattr(cli, "recover", recover)
    assert cli.main([]) == 0
    args = recover.await_args.args[0]
    assert args.hub == "192.168.100.2"
    assert args.token_file is None
    assert args.output is None


def test_identity_probe_recovers_after_a_dropped_udp_reply(monkeypatch):
    import sys
    from unittest.mock import AsyncMock

    attempts = []

    class Socket:
        def settimeout(self, _timeout):
            pass

        async def connect(self, _address):
            pass

        def sendto(self, packet):
            self.message_id = int(packet)

        async def recv(self, _size):
            attempts.append(self.message_id)
            if len(attempts) == 1:
                raise asyncio.TimeoutError()
            return json.dumps({"id": self.message_id, "result": {
                "model": IDENTITY.model, "fw_ver": IDENTITY.firmware,
                "mac": IDENTITY.mac,
            }}).encode()

        def close(self):
            pass

    protocol = sys.modules[core.AsyncMiIO.__module__]
    monkeypatch.setattr(protocol, "AsyncSocket", Socket)
    monkeypatch.setattr(core.AsyncMiIO, "ping", AsyncMock(return_value=True))
    monkeypatch.setattr(core.AsyncMiIO, "_pack_raw", lambda self, message_id, *_args: str(message_id).encode())
    monkeypatch.setattr(core.AsyncMiIO, "_unpack_raw", lambda self, packet: packet)
    assert asyncio.run(core.async_probe_gateway("192.168.100.2", "0" * 32)) == IDENTITY
    assert len(attempts) == 2
