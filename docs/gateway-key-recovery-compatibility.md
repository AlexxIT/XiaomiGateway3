# Recovery compatibility and verification

Only global/EU Xiaomi Smart Home Hub 2, runtime model `lumi.gateway.mgl001`,
stock firmware `1.0.8_0013`, is enabled by this utility.

| Device/build | Evidence | Status |
|---|---|---|
| Hub 2 `lumi.gateway.mgl001`, `1.0.8_0013` | One physical device returned a validated encrypted configuration export. The key authenticated existing Gateway3 setup. | Enabled |
| Other global Hub 2 builds | No physical recovery verification | Unverified and disabled |
| Mainland Hub 2 `lumi.gateway.mcn001` | No physical recovery verification, including the same `1.0.8_0013` version string | Unverified and disabled |
| Original Multimode Gateway `lumi.gateway.mgl03`, stock `1.5.7_0001` | Limited firmware-handler emulation returned fixed system logs and ignored the selected-file request | This handler does not provide the tested recovery route; disabled |
| Other original Multimode builds and Aqara hubs | No matching physical recovery verification | Unverified and disabled |

The original-gateway emulation redirected log-directory and agent-socket paths
into disposable locations and used a synthetic agent and logs. It tested file
selection only, not ordinary MIIO authentication or a physical gateway. It does
not rule out other recovery methods. No firmware files or binary analysis are
included in this contribution.

Marketing names and matching version strings do not establish compatibility.
The same RPC name can implement different behaviour. Do not bypass the model/build
checks to try a different device. Older token-only firmware already has its
existing recovery path in Gateway3.

## What was verified

The recovered key subsequently worked with the existing physical Gateway3 setup.
Four mesh lights passed local basic control and restoration, and the integration
reconnected after one ordinary hub reboot. Selected light modes were also tested.
This does not establish every device feature, radio mode or firmware variant.
Telnet enablement itself is existing upstream functionality.

The recovery tests use synthetic identities, credentials and encrypted archives.
They exercise malformed archive rejection, source restrictions, timeouts,
cancellation, cleanup and private-file handling without contacting a gateway.
Core/script tests passed on Python 3.10, 3.12 and 3.14 in the original development
runs. A source-preserving routed-network lab exercised a valid callback and a
blocked-return timeout. Those are client checks, not gateway reliability claims.

Recovery does not reset, flash or downgrade the gateway, clear a password or
start Telnet. The uploader can delete an existing `/tmp/log.tar.gz`, and firmware
debug logging can record export encryption settings and the callback URL.
Keep diagnostic logs private. See the [guide](gateway-key-recovery.md) for setup
side effects, troubleshooting and network prerequisites.

This contribution does not change regional registration, remove existing
Gateway3 network recommendations or prove ZHA, Zigbee2MQTT, Matter or multiple-HA
compatibility. Independent matching-device reproduction is still needed before
widening support. The optional Home Assistant recovery flow uses this same build restriction.
Its backend tests ran on HA 2026.10.1; actual frontend rendering and a complete
physical missing-key setup through that flow remain unverified.
