# Optional recovery during Home Assistant gateway setup

This optional setup flow uses the same engine as the [terminal recovery script](gateway-key-recovery.md).
It is limited to the same confirmed runtime model/build. It has not been deployed
to a live household or accepted upstream.

1. Add a physical gateway using its reachable LAN address and ordinary MIIO token.
   Leave Key absent only if you have no saved key. Existing cached/manual keys
   retain the normal setup path.
2. When Telnet is closed, identity matches the enabled profile and Home Assistant
   supports cancellable progress tasks, setup offers recovery. Review the LAN
   callback address. Alternatively enter an existing key.
3. Explicitly consent to recovery. The temporary HTTP receiver reads only
   `/data/miio/device.conf`; recovery neither opens Telnet nor clears passwords.
   Firmware can delete an old diagnostic archive and log export encryption
   settings, as described in the recovery guide.
4. Wait for a validated upload. An RPC acknowledgement is not success. Cancelling
   the flow cancels its task and closes the receiver. Failures offer a retry or a
   manual key without showing credentials or exception details.
5. Successful recovery opens a separate acknowledgement step before physical
   Gateway3 setup. That existing setup command clears the executing user's
   password and starts Telnet. Accept only if you want to enable that access.

The task stores its validated key privately and returns no credential-bearing
result. If the later setup check fails, a same-address/same-token retry reuses the
key instead of exporting it again. Successful setup uses the existing integration
entry/key persistence behaviour.

The advertised minimum HA version remains 2023.2. Recovery is offered only if
`async_show_progress` explicitly supports `progress_task`; older APIs retain
existing setup/manual-key behaviour. Native flow tests ran on HA 2026.10.1 and
also simulated the older signature. Additional backend tests exercised HA-driven
flow cancellation and a real HTTP upload with encrypted archive validation,
using simulated MIIO identity/dispatch and final gateway setup. They do not prove frontend rendering on every
HA version or actual device behaviour of this new UI.

The local callback address must be assigned to the HA process and reachable from
the hub. The native flow chooses an ephemeral port. Container port forwarding,
NAT, proxies or firewall rules can prevent the callback; use the standalone
utility with a reachable address and explicit `--port` when needed. Do not expose
HA authentication or the receiver publicly to work around this.
