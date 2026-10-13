# Recover your Hub 2 gateway key

On newer Hub 2 firmware, Gateway3 needs a **gateway key** to enable Telnet during
setup. This is a personalised 16-character value stored on the hub, separate
from the 32-character hexadecimal **Mi Home token** you obtain from your account.
The token authenticates local MIIO requests; the key authenticates the hub's
`system_command` setup command. Without the key, setup reports
“Unsupported gateway firmware without key”.

On the global/EU Xiaomi Smart Home Hub 2 (also called Multimode Gateway 2),
`lumi.gateway.mgl001` running stock **`1.0.8_0013`**, its diagnostic upload can
return the config file containing that key using the existing token. This guide
explains two ways to recover it:

1. **Home Assistant, recommended:** recover and save the key during gateway setup.
2. **Python script:** recover it on a computer and paste it into Gateway3.

## Before you start

Check the hub's firmware version in Xiaomi Home's device settings under firmware
update/device information. Recovery currently accepts only the model and build
above. Other firmware builds need their own verification.

Obtain the hub's [Mi Home token](../README.md#obtain-mi-home-device-token).
Home Assistant or your computer must reach the hub over UDP port 54321, and the
hub must be able to open an HTTP connection back to the recovery receiver.
Use local IPv4 addresses in `192.168.x.x`, `10.x.x.x` or `172.16.x.x` through
`172.31.x.x`. The receiver checks that uploads come from the hub's address, so
routing must preserve that source address.

## Get this PR's version

Until this feature is merged, check out the contribution:

```sh
git clone https://github.com/AlexxIT/XiaomiGateway3.git
cd XiaomiGateway3
git fetch origin pull/1781/head
git switch --detach FETCH_HEAD
```

## Option 1: Home Assistant

Back up your existing `config/custom_components/xiaomi_gateway3` folder. Replace
it with `custom_components/xiaomi_gateway3` from the checkout above and restart
Home Assistant. This installs the integration code for this PR.

1. Add **Xiaomi Gateway 3** and select the gateway from the Mi Cloud device list.
   Its IP address and token are filled in for you. Alternatively, choose
   **Add Gateway using Token** and enter those details.
2. Leave **Key** empty. On the supported build, setup offers key recovery.
3. Check the suggested Home Assistant address and select the recovery checkbox.
   The hub sends its reply to this address. Recovery takes up to 90 seconds.
4. Confirm gateway setup after the key is recovered. Gateway3's usual setup
   enables Telnet and clears the hub's root password.

Successful setup saves the key with the gateway entry. If subsequent setup
fails, retrying the same IP/token reuses the recovered key. You can also enter
an existing key manually. Closing the dialog during recovery cancels the task
and closes the temporary receiver.

For Docker installations, use host networking or arrange a reachable callback
address and port. The script is useful when the hub cannot reach your HA
container. Older HA versions without cancellable progress tasks retain manual
key entry; the new backend was tested on HA 2026.10.1.

## Option 2: Python script

Use Linux or macOS with Python 3.10 or later. From the checkout above:

```sh
python3 -m venv .venv
.venv/bin/pip3 install aiohttp cryptography
.venv/bin/python3 scripts/recover_gateway_key.py
```

Enter the hub's IP address and paste its Mi Home token at the prompts. The
script chooses your computer's local address, recovers the key and prints
`Gateway key: ...`. Copy that value into Gateway3's **Key** field.

Use `--callback-address YOUR_COMPUTER_IP` if automatic address selection chooses
the wrong interface. Optional `--port` fixes the receiver port, `--timeout`
changes the wait, and `--output` saves the key to a new JSON file. Run `--help`
for the full argument list.

## What changes on the hub

Recovery requests `/data/miio/device.conf`; the receiver decrypts and validates
it in memory. Telnet/password changes happen in Gateway3's subsequent setup.
On this firmware, successful-upload cleanup removes `/tmp/log.tar.gz` if that
temporary diagnostic bundle exists. Firmware debug logging can record the
one-off export encryption settings and callback URL. These behaviours were
identified in the firmware; deletion of an existing archive was not observed
during physical recovery.

## Troubleshooting

| Error | What to check |
|---|---|
| `cannot_connect` | Hub power, IP address and UDP connectivity. Retry after restoring the connection. |
| `invalid_token` | Obtain the current Mi Home token for this hub. |
| `unsupported_firmware` | Compare the exact model/build with the supported build above. |
| `invalid_input` | Use a local IPv4 address and a 32-character hexadecimal token. |
| `invalid_identity` | The hub's identity response was incomplete or malformed. |
| `callback_unavailable` | Check the receiver address and port. In HA, edit the suggested address. |
| `method_rejected` | The hub rejected the diagnostic request; record the model/build and error. |
| `upload_timeout` | Allow the hub's HTTP connection back to the receiver; check firewall and routing. |
| `invalid_upload` | The returned archive failed validation; include the error and model/build in a report. |

The script prints error codes as JSON. HA displays the corresponding translated
message. Keep the token and recovered key private when reporting results.

## How recovery works

The shared recovery code sends the token-authenticated
`async_device_feedback_log` request. Both `fileList` and `filelist` select
`/data/miio/device.conf`, matching the successful physical request. It supplies
a callback URL and fresh random 16-byte AES key and IV, encoded as padded
URL-safe base64.

The hub returns an HTTP PUT containing an AES-128-CBC/PKCS#7 encrypted USTAR
archive (uncompressed tar). The receiver accepts one regular `device.conf`
file, verifies its model and MAC against the hub's identity, and reads the
16-character gateway key. It checks the source address and callback path,
bounds the upload to 1 MiB and config file to 64 KiB, and closes the receiver
when finished or cancelled. The HA flow and script use this same implementation.

## What was tested

On one physical `lumi.gateway.mgl001` with stock `1.0.8_0013`, the recovered key
worked with Gateway3's normal setup, local device control and automatic
reconnection after a normal hub reboot. The hub was connected to the router by
Ethernet; the recovery computer used Wi-Fi on the same local network.

A limited firmware-handler emulation of the original Multimode Gateway
`lumi.gateway.mgl03` on `1.5.7_0001` returned fixed system logs rather than the
requested config. That test used synthetic logs and redirected temporary paths;
it verified file selection, rather than MIIO authentication or physical support.
Recovery remains enabled only for the confirmed Hub 2 model/build.

Synthetic tests cover encrypted HTTP uploads, archive/identity validation,
script input/output, HA progress, cancellation, retries and error handling.
The new HA screens and complete physical setup through them are open for testing.
Please include model, firmware build and connection details with your results.
