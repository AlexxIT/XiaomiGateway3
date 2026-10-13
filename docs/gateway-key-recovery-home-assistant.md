# Recover the key in Home Assistant

The recovery step is part of adding a gateway in this PR's version of Gateway3.
Choose a gateway from your Mi Cloud list to fill its address and token, or enter
those details using **Add Gateway using Token**. Leave Key empty.

On the supported build, setup offers to recover the key. It suggests HA's local
address for the gateway's reply. Confirm recovery and wait, then accept the
Telnet/password setup step. Successful setup saves the key with the entry.

A failed recovery offers retry or manual key entry. A failed subsequent setup
reuses the recovered key when retrying the same address/token. Closing the setup
dialog during recovery cancels the request and closes its temporary receiver.

## Connection requirements

The gateway needs to reach the suggested HA address on the temporary receiver's
TCP port. On a container installation, use host networking or arrange the return
connection. If that is inconvenient, run the [Python script](gateway-key-recovery.md#with-the-python-script)
on a computer connected to the gateway's local network.

## HA compatibility

The recovery step uses HA's cancellable progress-task API. On older HA versions,
the normal manual-key setup remains available. Backend tests ran on HA 2026.10.1.
The new screen and full physical-device flow are open for testing.
