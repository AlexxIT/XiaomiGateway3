# Recover your Hub 2 gateway key

Supports global/EU Smart Home Hub 2 (`lumi.gateway.mgl001`) on firmware
`1.0.8_0013`. You need its Mi Home token and a connection to its local network.

There are two ways to recover the key:

1. **Home Assistant, recommended:** recover it while adding the gateway.
2. **Python script:** run it on your computer and copy the key into Home Assistant.

## In Home Assistant

With this PR's version of Gateway3 installed:

1. Add Xiaomi Gateway 3 and choose your gateway from the Mi Cloud list, or choose
   **Add Gateway using Token** and enter its IP address and token. Selecting a
   cloud-listed gateway fills those details for you.
2. Leave Key empty. When recovery is available, accept the suggested callback
   address and select the recovery checkbox.
3. Wait for the key to be recovered, then confirm gateway setup. This enables
   Telnet and clears the gateway password, as Gateway3 normally does.

Home Assistant saves the key with the gateway's settings. The flow is open for
physical-device testing. See [HA setup details](gateway-key-recovery-home-assistant.md)
if recovery cannot complete.

## With the Python script

Use Linux or macOS with Python 3.10 or later. Obtain the gateway's
[Mi Home token](../README.md#obtain-mi-home-device-token).

Clone the repo and check out this PR:

```sh
git clone https://github.com/AlexxIT/XiaomiGateway3.git
cd XiaomiGateway3
git fetch origin pull/1781/head
git switch --detach FETCH_HEAD
```

Install the dependencies and run the script:

```sh
python3 -m venv .venv
.venv/bin/pip3 install aiohttp cryptography
.venv/bin/python3 scripts/recover_gateway_key.py
```

Enter the gateway IP address and paste its Mi Home token at the prompts.
The script detects your computer's local address, recovers the key and prints
`Gateway key: ...`. Copy that key into Gateway3's Key field.

The tested hub was connected to the router by Ethernet; the computer used Wi-Fi.
Both communicated through the local network.

## Troubleshooting

| Problem | What to check |
|---|---|
| Cannot connect or invalid token | Gateway IP, power and Mi Home token |
| Unsupported firmware | The supported model/build at the top of this guide |
| Upload times out | Allow the gateway to connect back to HA or the computer. Check the firewall and routing. |
| Wrong local address detected | For the script, supply `--callback-address YOUR_COMPUTER_IP`. In HA, edit the suggested address. |
| Upload fails validation | Keep the error code and model/build when reporting it. Keep the token and key private. |

The script also supports `--port` for a fixed receiver port and `--output` to
save the key to a new JSON file. Run it with `--help` for these optional settings.

[Technical details and verification](gateway-key-recovery-compatibility.md)
