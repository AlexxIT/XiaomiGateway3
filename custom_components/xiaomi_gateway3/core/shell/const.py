# rewrite log every time to prevent memory overflow
OPENMIIO_CMD = "/data/openmiio_agent miio mqtt cache central z3 --zigbee.tcp=8888 > /var/log/openmiio.log 2>&1 &"
OPENMIIO_BASE = "https://github.com/AlexxIT/openmiio_agent/releases/download/v1.2.1/"
OPENMIIO_MD5_MIPS = "6c3f4dca62647b9d19a81e1ccaa5ccc0"
OPENMIIO_MD5_ARM = "bb0b33b8d71acbfb9668ae9a0600c2d8"
OPENMIIO_URL_MIPS = OPENMIIO_BASE + "openmiio_agent_mips"
OPENMIIO_URL_ARM = OPENMIIO_BASE + "openmiio_agent_arm"
