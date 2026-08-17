#!/usr/bin/env python3
"""Store a DeepSeek key in the operating-system credential vault."""

from __future__ import annotations

import argparse
import getpass
import sys


SERVICE = "mpi-strategy-c-deepseek"
ACCOUNT = "default"


def keyring_module():
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("Python package 'keyring' is required") from exc
    return keyring


def get_secret() -> str | None:
    return keyring_module().get_password(SERVICE, ACCOUNT)


def native_prompt() -> str:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("MPI Strategy C")
        root.resizable(False, False)
        value = tk.StringVar()
        tk.Label(root, text="DeepSeek API Key").pack(padx=24, pady=(18, 6))
        entry = tk.Entry(root, textvariable=value, show="*", width=48)
        entry.pack(padx=24, pady=6)
        entry.focus_set()
        accepted = {"value": False}

        def accept() -> None:
            accepted["value"] = True
            root.destroy()

        tk.Button(root, text="Save securely", command=accept).pack(pady=(6, 18))
        root.bind("<Return>", lambda _event: accept())
        root.mainloop()
        if not accepted["value"]:
            return ""
        return value.get()
    except Exception:
        if not sys.stdin.isatty():
            return ""
        return getpass.getpass("DeepSeek API key (hidden): ")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    keyring = keyring_module()
    if args.check:
        present = bool(keyring.get_password(SERVICE, ACCOUNT))
        print("present" if present else "missing")
        return 0 if present else 1
    secret = native_prompt().strip()
    if not secret:
        print("No credential was saved.", file=sys.stderr)
        return 1
    if not secret.startswith("sk-") or len(secret) < 20:
        print("The value does not look like a DeepSeek API key.", file=sys.stderr)
        return 1
    keyring.set_password(SERVICE, ACCOUNT, secret)
    del secret
    print("DeepSeek credential saved in the operating-system credential vault.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
