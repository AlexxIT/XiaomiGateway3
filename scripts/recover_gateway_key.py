#!/usr/bin/env python3
"""Recover a Hub 2 gateway key. Run from a Gateway3 source checkout.

Enter the gateway IP address and paste its Mi Home token when prompted.
Requires aiohttp and cryptography.
"""

import argparse
import getpass
import asyncio
import importlib.util
import json
import os
import stat
import sys
import types
from pathlib import Path


def load_core():
    """Load the shared core without importing the Home Assistant integration."""
    folder = (
        Path(__file__).resolve().parents[1] / "custom_components/xiaomi_gateway3/core"
    )
    package_name = "gateway_key_recovery_cli"
    package = types.ModuleType(package_name)
    package.__path__ = [str(folder)]
    sys.modules[package_name] = package
    name = package_name + ".key_recovery"
    spec = importlib.util.spec_from_file_location(name, folder / "key_recovery.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read_private_token(path):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd) as file:
        info = os.fstat(file.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_mode & 0o077
            or info.st_uid != os.geteuid()
        ):
            raise ValueError("private_token_file_required")
        token = file.read(65).strip()
        if len(token) != 32 or any(c not in "0123456789abcdefABCDEF" for c in token):
            raise ValueError("invalid_token_file")
        return token


def reserve_output(path):
    return os.open(
        path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600
    )


async def recover(args, core):
    token = (
        read_private_token(args.token_file)
        if args.token_file
        else getpass.getpass("Mi Home token: ").strip()
    )
    descriptor = reserve_output(args.output) if args.output else None
    saved = False
    try:
        identity = await core.async_probe_gateway(args.hub, token)
        key = await core.async_recover_gateway_key(
            args.hub,
            token,
            args.callback_address,
            identity=identity,
            timeout=args.timeout,
            port=args.port,
            experimental=False,
        )
        if descriptor is not None:
            with os.fdopen(descriptor, "w") as output:
                descriptor = None
                json.dump(
                    {"model": identity.model, "firmware": identity.firmware,
                     "mac": identity.mac, "key": key}, output,
                )
                output.flush()
                os.fsync(output.fileno())
        saved = True
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if not saved and args.output:
            args.output.unlink(missing_ok=True)
    print(f"Gateway key: {key}")
    if args.output:
        print(f"Saved to {args.output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hub", help="Gateway IP address; prompted if omitted")
    parser.add_argument(
        "--token-file",
        type=Path,
        help="Read the token from a file instead of prompting",
    )
    parser.add_argument("--callback-address", help="This computer's reachable LAN IPv4")
    parser.add_argument(
        "--port", type=int, default=0, help="Receiver port; 0 chooses a free port"
    )
    parser.add_argument(
        "--output", type=Path, help="Also save the key to a new JSON file"
    )
    parser.add_argument(
        "--timeout", type=float, default=90, help="Upload wait, 1 to 300 seconds"
    )
    args = parser.parse_args(argv)
    try:
        if not args.hub:
            args.hub = input("Gateway IP address: ").strip()
        core = load_core()
        asyncio.run(recover(args, core))
    except KeyboardInterrupt:
        print(json.dumps({"error": "cancelled"}), file=sys.stderr)
        return 1
    except Exception as error:  # noqa: BLE001
        # No exception repr, traceback, MIIO params, key or token in normal output.
        code = (
            error.code if hasattr(error, "code") else "private_file_or_recovery_error"
        )
        print(json.dumps({"error": code}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
