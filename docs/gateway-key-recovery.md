# Recover a gateway key through the stock feedback uploader

This method recovered the personalised gateway key on a global/EU Xiaomi Smart
Home Hub 2 (`lumi.gateway.mgl001`) with stock firmware `1.0.8_0013`. It used an
ordinary MIIO token and an encrypted diagnostic upload. Recovery required no
UART, case opening, firmware flashing, downgrade, Telnet or password change.

The recovered key subsequently authenticated Gateway3's existing `system_command`
setup. Physical local control and automatic runtime recovery after one ordinary
reboot were verified on that device. This is one-device evidence, not a guarantee
for every model, firmware, radio mode or network configuration.

Telnet enablement is existing upstream work. This contribution supplies a missing
credential where the selected-file upload route is available. It does not claim
a new Telnet method or establish who first discovered the diagnostic route.

## Supported recovery builds

| Model | Firmware | Recovery evidence | Tool default |
|---|---|---|---|
| `lumi.gateway.mgl001` | `1.0.8_0013` | Actual matching encrypted export; key authenticated subsequent setup | Enabled |
| Other builds/models | [Compatibility report](gateway-key-recovery-compatibility.md) | Individual analysis required | Disabled |

The [compatibility summary](gateway-key-recovery-compatibility.md) distinguishes
physical recovery from limited firmware emulation and unverified builds.
A catalogue listing or matching string does not establish compatibility. The
`--experimental` flag permits only explicit analysed profiles; it does not bypass
model/build checks. No experimental profiles are currently enabled.

Older token-only firmware can already recover its key using the existing
integration. Use that existing path where applicable. Aqara Hub E1 and unrelated
Xiaomi gateways are outside this method's confirmed scope.

## Before starting

1. Identify the runtime model and exact installed build. Marketing names alone
   are insufficient. The utility verifies token-authenticated `miIO.info` before
   requesting a file and refuses an unsupported build.
2. Obtain the ordinary 32-hex-character MIIO token for your own gateway using an
   authorised account or the existing [token instructions](../README.md#obtain-mi-home-device-token).
   A stock OTA image cannot contain your personalised gateway key.
3. Use a Linux or macOS computer with Python 3.10 or later and a current source
   checkout containing this utility. Dependencies are `aiohttp` and `cryptography`.
4. Choose the computer's LAN IPv4 address that the gateway can reach. Only private
   IPv4 addresses are accepted. Permit the gateway to make an HTTP PUT to the
   selected TCP port, and permit the computer's MIIO UDP connection to port 54321.
   Recovery uses plain HTTP because that is the validated firmware upload path.
5. Keep the gateway's existing registration and firmware. Resetting, unbinding,
   Android, Bluetooth and region migration are not recovery prerequisites proven
   by this method. The actual recovery used Ethernet; Wi-Fi was not tested.

Do not disable your HA authentication or expose the receiver to the internet.
The temporary endpoint accepts only the gateway's source address and a random
URL. Routing/NAT must preserve that address. This does not remove Gateway3's
separate firmware and [network requirements](../README.md#network-configuration).

## Run from a source checkout

Clone this contribution's source branch and change into the checkout. Do not
copy the script alone: it loads the adjacent shared recovery module and existing
MIIO transport without importing Home Assistant.

Create a private directory:

```sh
umask 077
mkdir -p "$HOME/.xiaomi-gateway-private"
chmod 700 "$HOME/.xiaomi-gateway-private"
```

Save the ordinary token without placing it in command arguments or shell history:

```sh
python3 - <<'PY'
import getpass, os
from pathlib import Path
path = Path.home() / '.xiaomi-gateway-private' / 'token'
token = getpass.getpass('Own gateway MIIO token: ').strip()
if len(token) != 32 or any(c not in '0123456789abcdefABCDEF' for c in token):
    raise SystemExit('Expected a 32-character hexadecimal token')
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
with os.fdopen(fd, 'w') as file:
    file.write(token)
PY
```

Inspect the CLI and run it, replacing the example addresses with your own hub
and this computer's reachable LAN address:

```sh
python3 scripts/recover_gateway_key.py --help
uv run --with aiohttp --with cryptography python3 scripts/recover_gateway_key.py \
  --hub 192.168.100.10 \
  --callback-address 192.168.100.20 \
  --token-file "$HOME/.xiaomi-gateway-private/token" \
  --output "$HOME/.xiaomi-gateway-private/gateway-key.json"
```

Alternatively install the two dependencies in a Python virtual environment.
The callback address can be omitted if the automatically selected local route is
reachable from the hub. `--port` defaults to an ephemeral port; specify a fixed
port if your firewall needs one. `--timeout` defaults to 90 seconds.

Success prints only `key_saved` and `key_not_printed`. The new output file is
owner-only and includes the verified model, firmware, MAC and key. Store the key
privately, then enter it in Gateway3's existing gateway setup. An existing output
file is never overwritten. A failed/cancelled export removes its empty reserved
output and closes the listener. Do not repeat recovery after saving the key.

Adding the physical Gateway3 entry is a separate operation: the existing setup
command clears the executing user's password and starts Telnet. Recovery itself
does neither. Restrict subsequent Telnet access to your trusted LAN.

## Request and response format

On the tested device, a token-authenticated `async_device_feedback_log` request
exported `device.conf` containing its model, MAC and personalised gateway key.
The utility uses this observable exchange; it does not reproduce vendor firmware
code or derive a key from a firmware image.

The request includes both `fileList` and `filelist`, each containing only
`/data/miio/device.conf`, to match the successful request on the tested build.
It supplies independently generated 16-byte export encryption key and IV as
padded URL-safe base64 (24 characters each), plus the receiver URL. These export
settings are distinct from both the MIIO token and the gateway key being recovered.

The firmware sends an HTTP PUT containing AES-128-CBC/PKCS#7 encrypted USTAR,
not gzip. The utility decrypts in memory and accepts exactly one regular-file
`device.conf`, verifies model/MAC and validates the 16-character gateway key.
It never extracts archive paths or requests arbitrary files.

The uploader may delete an existing `/tmp/log.tar.gz` after an explicit-file
upload. Do not describe recovery as completely side-effect-free. Firmware debug code
also logs the export encryption settings and URL; keep raw diagnostic logs
private. Client-side redaction does not remove those firmware log statements.

## Troubleshooting and proof boundaries

- `cannot_connect`: no usable token-authenticated identity response. Check hub IP,
  UDP reachability and power without resetting the hub.
- `invalid_token`: the MIIO client saw a device handshake but could not obtain a
  valid identity response. This distinction is diagnostic, not proof of the exact
  firmware rejection reason. Refresh the authorised token if necessary.
- `unsupported_firmware`: this exact model/build has no enabled recovery profile.
  Manual-key and existing supported setup paths remain available.
- `callback_unavailable`: the local receiver could not bind/select an address.
  Use an address assigned to this computer and an available port.
- `method_rejected`: the gateway explicitly rejected the diagnostic RPC. Do not
  substitute unrelated model profiles or guess alternate passwords.
- `upload_timeout`: no valid upload arrived. An RPC acknowledgement alone is not
  success. Check the return path and firewall; firmware support may be uncertain.
- `invalid_upload`: the ciphertext, archive, identity or key failed validation.
  The utility does not weaken those checks or save partial data.

The synthetic test suite exercises receiver bounds, authentication, archive
validation, cancellation and private storage. An isolated routed-network lab
also verified a successful callback across two subnets and a timeout when the
return route was blocked. Those tests validate this client, not gateway firmware
stability across subnets, Wi-Fi router settings, regional enrolment or all radio
modes. Do not change the README's broader recommendations based on this test.
