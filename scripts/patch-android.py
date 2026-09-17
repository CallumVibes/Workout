#!/usr/bin/env python3
"""
Patches the Android project that Capacitor generates.

Run by CI after `npx cap add android`. Everything here is idempotent, so
running it twice on the same project changes nothing the second time.

Three jobs:
  1. Declare the permissions local notifications need on Android 13+.
  2. Register the groundwork:// deep link so Amber can hand results back.
  3. Declare that we look for a nostrsigner, which Android 11+ hides otherwise.
"""

import json
import os
import sys

MANIFEST = "android/app/src/main/AndroidManifest.xml"
ASSET_CFG = "android/app/src/main/assets/capacitor.config.json"

PERMISSIONS = [
    "android.permission.POST_NOTIFICATIONS",
    "android.permission.SCHEDULE_EXACT_ALARM",
    "android.permission.RECEIVE_BOOT_COMPLETED",
    "android.permission.VIBRATE",
    "android.permission.INTERNET",
]

DEEP_LINK = """
            <intent-filter>
                <action android:name="android.intent.action.VIEW" />
                <category android:name="android.intent.category.DEFAULT" />
                <category android:name="android.intent.category.BROWSABLE" />
                <data android:scheme="groundwork" />
            </intent-filter>
        </activity>"""

SIGNER_QUERY = """    <queries>
        <intent>
            <action android:name="android.intent.action.VIEW" />
            <data android:scheme="nostrsigner" />
        </intent>
    </queries>
</manifest>"""


def patch_manifest():
    if not os.path.exists(MANIFEST):
        sys.exit(f"Could not find {MANIFEST} — did `npx cap add android` run?")

    xml = open(MANIFEST, encoding="utf-8").read()
    changed = []

    for perm in PERMISSIONS:
        if perm not in xml:
            xml = xml.replace(
                "<application",
                f'<uses-permission android:name="{perm}" />\n    <application',
                1,
            )
            changed.append(perm.rsplit(".", 1)[-1])

    if 'android:scheme="groundwork"' not in xml:
        xml = xml.replace("</activity>", DEEP_LINK, 1)
        changed.append("groundwork:// deep link")

    if "nostrsigner" not in xml:
        xml = xml.replace("</manifest>", SIGNER_QUERY, 1)
        changed.append("nostrsigner visibility")

    open(MANIFEST, "w", encoding="utf-8").write(xml)
    print("Manifest:", ", ".join(changed) if changed else "already up to date")


def patch_config():
    if not os.path.exists(ASSET_CFG):
        print("Config: no bundled config yet, skipping")
        return
    cfg = json.load(open(ASSET_CFG, encoding="utf-8"))
    cfg.setdefault("server", {})["androidScheme"] = "https"
    json.dump(cfg, open(ASSET_CFG, "w", encoding="utf-8"), indent=2)
    print("Config: androidScheme set to https")


if __name__ == "__main__":
    patch_manifest()
    patch_config()
