import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.xiaomi_gateway3 import config_flow
from custom_components.xiaomi_gateway3.core import key_recovery
from custom_components.xiaomi_gateway3.core.const import DOMAIN


HOST = "192.168.100.10"
TOKEN = "0123456789abcdef0123456789abcdef"
CALLBACK = "192.168.100.20"
KEY = "abcdef0123456789"
IDENTITY = key_recovery.GatewayIdentity(
    "lumi.gateway.mgl001",
    "1.0.8_0013",
    "00:11:22:33:44:55",
)


@pytest.fixture(autouse=True)
def _isolate_config_entry_creation(enable_custom_integrations, monkeypatch):
    """Capture entry data without setting up the integration or opening sockets."""
    def capture_entry(self, title, data, options=None):
        self._test_created_entry = {
            "title": title,
            "data": data,
            "options": options,
        }
        return self.async_abort(reason="entry_captured")

    monkeypatch.setattr(config_flow.FlowHandler, "async_create_entry", capture_entry)
    yield


@pytest.fixture
def flow_handlers(monkeypatch):
    handlers = []
    original = config_flow.FlowHandler.async_step_token

    async def capture(self, user_input=None):
        if self not in handlers:
            handlers.append(self)
        return await original(self, user_input)

    monkeypatch.setattr(config_flow.FlowHandler, "async_step_token", capture)
    return handlers


def _mock_supported_missing_key(monkeypatch):
    check_port = AsyncMock(return_value=False)
    probe = AsyncMock(return_value=IDENTITY)
    supports = Mock(return_value=True)
    callback = Mock(return_value=CALLBACK)
    recover = AsyncMock(return_value=KEY)
    gateway_info = AsyncMock(return_value={"model": IDENTITY.model})
    restore = AsyncMock(return_value=None)

    monkeypatch.setattr(config_flow.hass_utils, "get_cloud_gateways", lambda _hass: [])
    monkeypatch.setattr(config_flow.hass_utils, "restore_gateway_key", restore)
    monkeypatch.setattr(config_flow.core_utils, "check_port", check_port)
    monkeypatch.setattr(key_recovery, "async_probe_gateway", probe)
    monkeypatch.setattr(key_recovery, "supports_recovery", supports)
    monkeypatch.setattr(key_recovery, "callback_ipv4", callback)
    monkeypatch.setattr(key_recovery, "async_recover_gateway_key", recover)
    monkeypatch.setattr(config_flow.core_utils, "gateway_info", gateway_info)

    return {
        "check_port": check_port,
        "probe": probe,
        "supports": supports,
        "callback": callback,
        "recover": recover,
        "gateway_info": gateway_info,
        "restore": restore,
    }


async def _start_token_flow(hass: HomeAssistant) -> str:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    flow_id = result["flow_id"]
    result = await hass.config_entries.flow.async_configure(
        flow_id, {"action": "token"}
    )
    assert result["step_id"] == "token"
    return flow_id


async def _submit_token(hass: HomeAssistant, flow_id: str, key: str = None):
    user_input = {"host": HOST, "token": TOKEN}
    if key is not None:
        user_input["key"] = key
    return await hass.config_entries.flow.async_configure(flow_id, user_input)


def _capture_entry(flow_handlers):
    assert len(flow_handlers) == 1
    return flow_handlers[0]._test_created_entry


def _gate_recovery(mocks, result=KEY):
    started = asyncio.Event()
    release = asyncio.Event()

    async def wait_for_result(*_args, **_kwargs):
        started.set()
        await release.wait()
        if isinstance(result, Exception):
            raise result
        return result

    mocks["recover"].side_effect = wait_for_result
    return started, release


@pytest.mark.asyncio
async def test_missing_key_on_confirmed_build_offers_opt_in_before_gateway_info(
    hass, monkeypatch, flow_handlers
):
    mocks = _mock_supported_missing_key(monkeypatch)
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id)

    assert result["step_id"] == "key_recovery"
    assert result["type"] == "form"
    mocks["check_port"].assert_awaited_once_with(HOST, 23)
    mocks["probe"].assert_awaited_once_with(HOST, TOKEN)
    mocks["supports"].assert_called_once_with(IDENTITY, experimental=False)
    mocks["callback"].assert_called_once_with(HOST)
    mocks["gateway_info"].assert_not_awaited()
    mocks["recover"].assert_not_awaited()
    assert flow_handlers


@pytest.mark.asyncio
async def test_legacy_progress_signature_keeps_existing_setup_path(
    hass, monkeypatch, flow_handlers
):
    mocks = _mock_supported_missing_key(monkeypatch)

    def legacy_show_progress(self, *, progress_action, step_id=None):
        return self.async_show_form(step_id=step_id or "legacy_progress")

    monkeypatch.setattr(
        config_flow.FlowHandler, "async_show_progress", legacy_show_progress
    )
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id)

    assert result["type"] == "abort"
    assert result["reason"] == "entry_captured"
    mocks["restore"].assert_awaited_once_with(hass, TOKEN)
    mocks["check_port"].assert_not_awaited()
    mocks["probe"].assert_not_awaited()
    mocks["supports"].assert_not_called()
    mocks["recover"].assert_not_awaited()
    mocks["gateway_info"].assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_build_keeps_existing_missing_key_path(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["supports"].return_value = False
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id)

    assert result["type"] == "abort"
    assert result["reason"] == "entry_captured"
    mocks["gateway_info"].assert_awaited_once()
    mocks["recover"].assert_not_awaited()


@pytest.mark.asyncio
async def test_supplied_key_keeps_existing_setup_path(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id, KEY)

    assert result["type"] == "abort"
    assert result["reason"] == "entry_captured"
    assert _capture_entry(flow_handlers)["options"]["key"] == KEY
    mocks["restore"].assert_not_awaited()
    mocks["check_port"].assert_not_awaited()
    mocks["probe"].assert_not_awaited()
    mocks["recover"].assert_not_awaited()
    mocks["gateway_info"].assert_awaited_once()


@pytest.mark.asyncio
async def test_restored_key_takes_precedence_over_recovery(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["restore"].return_value = KEY
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id)

    assert result["type"] == "abort"
    assert result["reason"] == "entry_captured"
    assert _capture_entry(flow_handlers)["options"]["key"] == KEY
    mocks["restore"].assert_awaited_once_with(hass, TOKEN)
    mocks["check_port"].assert_not_awaited()
    mocks["probe"].assert_not_awaited()
    mocks["recover"].assert_not_awaited()
    mocks["gateway_info"].assert_awaited_once()


@pytest.mark.asyncio
async def test_open_telnet_keeps_existing_missing_key_path(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["check_port"].return_value = True
    flow_id = await _start_token_flow(hass)

    result = await _submit_token(hass, flow_id)

    assert result["type"] == "abort"
    assert result["reason"] == "entry_captured"
    mocks["check_port"].assert_awaited_once_with(HOST, 23)
    mocks["probe"].assert_not_awaited()
    mocks["recover"].assert_not_awaited()
    mocks["gateway_info"].assert_awaited_once()


@pytest.mark.asyncio
async def test_manual_key_can_be_resubmitted_on_setup_retry(
    hass, monkeypatch, flow_handlers
):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["gateway_info"].side_effect = [
        {"error": "cant_connect"},
        {"model": IDENTITY.model},
    ]
    flow_id = await _start_token_flow(hass)
    offered = await _submit_token(hass, flow_id)
    assert offered["step_id"] == "key_recovery"

    result = await hass.config_entries.flow.async_configure(
        flow_id,
        {"callback_address": CALLBACK, "key": KEY, "confirm_recovery": False},
    )

    assert result["step_id"] == "token"
    assert result["errors"] == {"base": "cant_connect"}
    mocks["gateway_info"].assert_awaited_once()

    retry = await hass.config_entries.flow.async_configure(
        flow_id, {"host": HOST, "token": TOKEN, "key": KEY}
    )

    assert retry["type"] == "abort"
    assert retry["reason"] == "entry_captured"
    assert _capture_entry(flow_handlers)["options"]["key"] == KEY
    mocks["check_port"].assert_awaited_once_with(HOST, 23)
    mocks["recover"].assert_not_awaited()
    assert mocks["gateway_info"].await_count == 2


@pytest.mark.asyncio
async def test_recovery_requires_explicit_consent(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": False}
    )

    assert result["step_id"] == "key_recovery"
    assert result["errors"] == {"base": "recovery_consent_required"}
    mocks["recover"].assert_not_awaited()
    mocks["gateway_info"].assert_not_awaited()


@pytest.mark.asyncio
async def test_recovered_key_needs_second_confirmation_before_gateway_info(
    hass, monkeypatch, flow_handlers
):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["gateway_info"].side_effect = [
        {"error": "cant_connect"},
        {"model": IDENTITY.model},
    ]
    started, release = _gate_recovery(mocks)
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)

    progress = await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": True}
    )
    assert progress["type"] == "progress"
    assert progress["progress_action"] == "recovering_key"
    await started.wait()
    flow = flow_handlers[0]
    task = flow._key_recovery_task
    mocks["gateway_info"].assert_not_awaited()

    release.set()
    await hass.async_block_till_done()

    assert task.result() is None
    assert flow._recovered_gateway_key == KEY
    assert mocks["gateway_info"].await_count == 0

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"confirm_setup": False}
    )
    assert result["step_id"] == "key_recovery_confirm"
    assert result["errors"] == {"base": "confirm_setup_required"}
    mocks["gateway_info"].assert_not_awaited()

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"confirm_setup": True}
    )
    assert result["step_id"] == "token"
    assert result["errors"] == {"base": "cant_connect"}
    assert mocks["gateway_info"].await_count == 1

    retry = await hass.config_entries.flow.async_configure(
        flow_id, {"host": HOST, "token": TOKEN}
    )
    assert retry["type"] == "abort"
    assert retry["reason"] == "entry_captured"
    assert _capture_entry(flow_handlers)["options"]["key"] == KEY
    mocks["check_port"].assert_awaited_once_with(HOST, 23)
    mocks["probe"].assert_awaited_once_with(HOST, TOKEN)
    mocks["recover"].assert_awaited_once()
    assert mocks["gateway_info"].await_count == 2
    assert mocks["gateway_info"].await_args_list[0].kwargs["key"] == KEY
    assert mocks["gateway_info"].await_args_list[1].kwargs["key"] == KEY


@pytest.mark.asyncio
async def test_timeout_is_safe_and_retryable(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    started, release = _gate_recovery(
        mocks, key_recovery.RecoveryError("upload_timeout")
    )
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)

    progress = await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": True}
    )
    assert progress["type"] == "progress"
    await started.wait()
    task = flow_handlers[0]._key_recovery_task
    release.set()
    await hass.async_block_till_done()

    flow = flow_handlers[0]
    assert task.result() is None
    failure_form = await hass.config_entries.flow.async_configure(flow_id)
    assert failure_form["step_id"] == "key_recovery"
    assert failure_form["errors"] == {"base": "upload_timeout"}
    assert TOKEN not in repr(failure_form)
    assert KEY not in repr(failure_form)
    mocks["gateway_info"].assert_not_awaited()

    started, release = _gate_recovery(mocks)
    retry = await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": True}
    )
    assert retry["type"] == "progress"
    await started.wait()
    retry_task = flow._key_recovery_task
    release.set()
    await hass.async_block_till_done()

    assert retry_task.result() is None
    assert flow._recovered_gateway_key == KEY
    assert mocks["recover"].await_count == 2
    mocks["gateway_info"].assert_not_awaited()


@pytest.mark.asyncio
async def test_unexpected_failure_is_redacted_and_retryable(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    secret_error = RuntimeError(f"device={TOKEN} recovered={KEY}")
    started, release = _gate_recovery(mocks, secret_error)
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)

    result = await hass.config_entries.flow.async_configure(
        flow_id, {"confirm_recovery": True}
    )
    assert result["type"] == "progress"
    await started.wait()
    task = flow_handlers[0]._key_recovery_task
    release.set()
    await hass.async_block_till_done()

    assert task.result() is None
    failure_form = await hass.config_entries.flow.async_configure(flow_id)
    assert failure_form["step_id"] == "key_recovery"
    assert failure_form["errors"] == {"base": "recovery_failed"}
    assert TOKEN not in repr(failure_form)
    assert KEY not in repr(failure_form)
    mocks["gateway_info"].assert_not_awaited()


@pytest.mark.asyncio
async def test_cancelling_recovery_does_not_continue_setup(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    started = asyncio.Event()
    cleaned_up = asyncio.Event()

    async def wait_until_cancelled(*_args, **_kwargs):
        started.set()
        try:
            await asyncio.Future()
        finally:
            cleaned_up.set()

    mocks["recover"].side_effect = wait_until_cancelled
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)
    progress = await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": True}
    )
    assert progress["type"] == "progress"

    await started.wait()
    task = flow_handlers[0]._key_recovery_task
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert cleaned_up.is_set()
    mocks["gateway_info"].assert_not_awaited()


@pytest.mark.asyncio
async def test_ha_abort_cancels_owned_recovery_task(hass, monkeypatch, flow_handlers):
    """Exercise HA's flow abort, rather than cancelling the task ourselves."""
    mocks = _mock_supported_missing_key(monkeypatch)
    started = asyncio.Event()
    closed = asyncio.Event()

    async def wait_for_upload(*args, **kwargs):
        started.set()
        try:
            await asyncio.Future()
        finally:
            closed.set()

    mocks["recover"].side_effect = wait_for_upload
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)
    await hass.config_entries.flow.async_configure(
        flow_id, {"callback_address": CALLBACK, "confirm_recovery": True}
    )
    await started.wait()
    task = flow_handlers[0]._key_recovery_task
    hass.config_entries.flow.async_abort(flow_id)
    await hass.async_block_till_done()
    assert task.cancelled()
    assert closed.is_set()
    mocks["gateway_info"].assert_not_awaited()


@pytest.mark.asyncio
async def test_flow_runs_real_receiver_and_archive_validation(
    hass, monkeypatch, flow_handlers
):
    """Real HA manager, recovery engine, HTTP PUT and encrypted archive parsing.

    Only MIIO identity/dispatch and final Telnet setup are simulated. No physical
    hub, real credentials or household network is involved.
    """
    import base64
    import io
    import tarfile
    import pytest_socket
    from aiohttp import ClientSession
    from cryptography.hazmat.primitives import padding
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    real_recover = key_recovery.async_recover_gateway_key
    mocks = _mock_supported_missing_key(monkeypatch)
    monkeypatch.setattr(key_recovery, "async_recover_gateway_key", real_recover)
    monkeypatch.setattr(key_recovery, "private_ipv4", lambda value: "127.0.0.1")
    receivers = []
    original_receiver = key_recovery.KeyReceiver

    class TrackedReceiver(original_receiver):
        def __init__(self, host, *args):
            super().__init__("127.0.0.1", *args)
            receivers.append(self)

    class SimulatedMIIO:
        def __init__(self, *args):
            pass

        async def send(self, method, params, **kwargs):
            assert method == "async_device_feedback_log"
            assert params["fileList"] == params["filelist"] == ["/data/miio/device.conf"]
            plain = io.BytesIO()
            payload = f"model={IDENTITY.model}\nmac={IDENTITY.mac}\nkey={KEY}\n".encode()
            with tarfile.open(fileobj=plain, mode="w", format=tarfile.USTAR_FORMAT) as archive:
                member = tarfile.TarInfo("device.conf")
                member.size = len(payload)
                archive.addfile(member, io.BytesIO(payload))
            padder = padding.PKCS7(128).padder()
            padded = padder.update(plain.getvalue()) + padder.finalize()
            encryptor = Cipher(
                algorithms.AES(base64.urlsafe_b64decode(params["encryptKey"])),
                modes.CBC(base64.urlsafe_b64decode(params["iv"])),
            ).encryptor()
            encrypted = encryptor.update(padded) + encryptor.finalize()
            async with ClientSession() as session:
                async with session.put(params["url"], data=encrypted) as response:
                    assert response.status == 200
            return {"result": {"code": 0}}

    monkeypatch.setattr(key_recovery, "AsyncMiIO", SimulatedMIIO)
    monkeypatch.setattr(key_recovery, "KeyReceiver", TrackedReceiver)
    pytest_socket.enable_socket()
    pytest_socket.socket_allow_hosts(["127.0.0.1", "::1"], allow_unix_socket=True)
    try:
        flow_id = await _start_token_flow(hass)
        offered = await _submit_token(hass, flow_id)
        assert offered["step_id"] == "key_recovery"
        progress = await hass.config_entries.flow.async_configure(
            flow_id, {"callback_address": "127.0.0.1", "confirm_recovery": True}
        )
        assert progress["type"] == "progress"
        await hass.async_block_till_done()
        flow = flow_handlers[0]
        assert flow._recovered_gateway_key == KEY
        assert len(receivers) == 1
        assert not receivers[0].runner.sites
        mocks["gateway_info"].assert_not_awaited()
        result = await hass.config_entries.flow.async_configure(flow_id, {"confirm_setup": True})
        assert result["type"] == "abort"
        assert _capture_entry(flow_handlers)["options"]["key"] == KEY
        mocks["gateway_info"].assert_awaited_once()
    finally:
        pytest_socket.disable_socket(allow_unix_socket=True)


@pytest.mark.asyncio
async def test_cleared_wrong_manual_key_offers_recovery_again(hass, monkeypatch, flow_handlers):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["gateway_info"].return_value = {"error": "wrong_telnet"}
    flow_id = await _start_token_flow(hass)
    await _submit_token(hass, flow_id)
    failed = await hass.config_entries.flow.async_configure(
        flow_id, {"key": KEY, "confirm_recovery": False}
    )
    assert failed["errors"] == {"base": "wrong_telnet"}
    result = await _submit_token(hass, flow_id, key="")
    assert result["step_id"] == "key_recovery"
    assert mocks["gateway_info"].await_count == 1
    assert mocks["probe"].await_count == 2
    hass.config_entries.flow.async_abort(flow_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["cannot_connect", "invalid_token"])
async def test_preflight_failure_does_not_claim_unsupported_firmware(
    hass, monkeypatch, flow_handlers, code, caplog
):
    mocks = _mock_supported_missing_key(monkeypatch)
    mocks["probe"].side_effect = key_recovery.RecoveryError(code)
    mocks["gateway_info"].return_value = {"error": "no_key"}
    flow_id = await _start_token_flow(hass)
    failed = await _submit_token(hass, flow_id)
    assert failed["step_id"] == "token"
    assert failed["errors"] == {"base": code}
    assert TOKEN not in caplog.text
    mocks["probe"].side_effect = None
    result = await _submit_token(hass, flow_id)
    assert result["step_id"] == "key_recovery"
    hass.config_entries.flow.async_abort(flow_id)
