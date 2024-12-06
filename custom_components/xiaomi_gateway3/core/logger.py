"""
Logging can be setup from:

1. Hass default config

```yaml
logger:
 logs:
   custom_components.xiaomi_gateway3: debug
```

2. Integration config (YAML)

```yaml
xiaomi_gateway3:
  logger:
    filename: xiaomi_gateway3.log
    propagate: False  # disable log to home-assistant.log and console
    max_bytes: 100000000
    backup_count: 3
```

3. Integration config (GUI)

Configuration > Xiaomi Gateway 3 > Configure > Debug
"""

import logging
import os
from logging import Formatter
from logging.handlers import RotatingFileHandler
from queue import SimpleQueue

import voluptuous as vol
from homeassistant.const import CONF_FILENAME
from homeassistant.helpers import config_validation as cv
from homeassistant.util.logging import HomeAssistantQueueHandler

FMT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"

CONFIG_SCHEMA = vol.Schema(
    {
        vol.Optional("level", default="debug"): cv.string,
        vol.Optional("propagate", default=True): cv.boolean,
        vol.Optional(CONF_FILENAME): cv.string,
        vol.Optional("mode", default="a"): cv.string,
        vol.Optional("max_bytes", default=0): cv.positive_int,
        vol.Optional("backup_count", default=0): cv.positive_int,
        vol.Optional("format", default=FMT): cv.string,
    },
    extra=vol.ALLOW_EXTRA,
)


def init(logger_name: str, config: dict, config_dir: str = None):
    level = config["level"].upper()

    logger = logging.getLogger(logger_name)
    logger.propagate = config["propagate"]
    logger.setLevel(level)

    filename = config.get(CONF_FILENAME)
    if filename:
        if config_dir:
            filename = os.path.join(config_dir, filename)

        file_handler = RotatingFileHandler(
            filename,
            config["mode"],
            config["max_bytes"],
            config["backup_count"],
        )

        fmt = Formatter(config["format"])
        file_handler.setFormatter(fmt)

        # copy logic from homeassistant/utils/logging.py
        queue: SimpleQueue[logging.Handler] = SimpleQueue()
        queue_handler = HomeAssistantQueueHandler(queue)
        queue_handler.listener = logging.handlers.QueueListener(queue, file_handler)
        queue_handler.listener.start()

        logger.addHandler(queue_handler)
