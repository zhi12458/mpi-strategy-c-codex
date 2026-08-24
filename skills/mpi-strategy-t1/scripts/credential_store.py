#!/usr/bin/env python3
"""Store the T1 DeepSeek key in the operating-system credential vault."""

from __future__ import annotations

import argparse
import getpass
import sys

from t1_runtime import load_lock


def keyring_module():
    try:
        import keyring
    except ImportError as exc:
        raise RuntimeError("Python package 'keyring' is required") from exc
    return keyring


def policy() -> tuple[str, str]:
    value = load_lock()["credential_policy"]
    return value["deepseek_service"], value["deepseek_account"]


def get_secret() -> str | None:
    service, account = policy()
    return keyring_module().get_password(service, account)


def native_prompt() -> str:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title("MPI T1 DeepSeek Credential")
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
        return value.get() if accepted["value"] else ""
    except Exception:
        if not sys.stdin.isatty():
            return ""
        return getpass.getpass("DeepSeek API key (hidden): ")


def normalize(value: str) -> str:
    stripped = value.strip()
    if stripped.casefold().startswith("bearer "):
        stripped = stripped[7:].strip()
    return stripped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="report only whether a credential exists")
    args = parser.parse_args()
    keyring = keyring_module()
    service, account = policy()
    if args.check:
        try:
            present = bool(keyring.get_password(service, account))
        except Exception:
            print("The operating-system credential vault is unavailable.", file=sys.stderr)
            return 2
        print("present" if present else "missing")
        return 0 if present else 1
    secret = normalize(native_prompt())
    if not secret:
        print("No credential was saved.", file=sys.stderr)
        return 1
    if not secret.startswith("sk-") or len(secret) < 20:
        print("The value does not look like a DeepSeek API key.", file=sys.stderr)
        return 1
    try:
        keyring.set_password(service, account, secret)
    except Exception:
        del secret
        print("The operating-system credential vault is unavailable; no credential was saved.", file=sys.stderr)
        return 2
    del secret
    print("DeepSeek credential saved in the T1 operating-system vault.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
