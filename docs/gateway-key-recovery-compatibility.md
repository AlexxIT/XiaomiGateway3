# Technical details and verification

## Supported build

Recovery is enabled for `lumi.gateway.mgl001` on stock `1.0.8_0013`.
A matching encrypted export on one physical hub produced a key that worked with
Gateway3. Four mesh lights passed basic control/restoration and Gateway3
reconnected after a normal hub reboot. The hub used Ethernet to its router;
the recovery computer used Wi-Fi.

Other builds can be investigated individually. The original Multimode Gateway
`lumi.gateway.mgl03` on `1.5.7_0001` returned fixed system logs in a limited
firmware-handler emulation test. That test used synthetic logs and redirected
temporary paths; it tested file selection rather than MIIO authentication.

## Recovery exchange

The script and HA flow use the token-authenticated `async_device_feedback_log`
request. Both `fileList` and `filelist` contain `/data/miio/device.conf`, matching
the successful request. The request supplies a callback URL and random 16-byte
AES key and IV, encoded as padded URL-safe base64.

The hub returns an HTTP PUT with an AES-128-CBC/PKCS#7 encrypted USTAR archive.
The receiver accepts a single regular `device.conf` file, checks its model/MAC
against the gateway identity and validates the 16-character key. Receiver size,
source-address and timeout checks bound the upload.

On this build, the firmware's successful-upload cleanup deletes
`/tmp/log.tar.gz` if that temporary diagnostic bundle exists. Its debug logging
can include the export encryption settings and callback URL. Those behaviours
were identified in the firmware; deletion of a pre-existing archive during the
physical recovery was not observed.

## Tests

Synthetic tests cover encrypted uploads, validation failures, cancellation,
receiver cleanup and script input/output. HA tests cover consent, progress,
retry, saved/manual keys and manager-driven cancellation. An integrated backend
test uses the actual HTTP receiver and archive validation with simulated MIIO
responses and final gateway setup.

The HA screen and complete physical-device setup through it are open for testing.
