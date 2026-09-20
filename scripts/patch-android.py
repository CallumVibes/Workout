#!/usr/bin/env python3
"""
Patches the Android project that Capacitor generates.

Run by CI after `npx cap add android`. Everything here is idempotent, so
running it twice on the same project changes nothing the second time.

Five jobs:
  1. Declare the permissions local notifications need on Android 13+.
  2. Register the groundwork:// deep link so a signer can hand results back.
  3. Declare that we look for a nostrsigner, which Android 11+ hides otherwise.
  4. Write the Amber plugin, which is the only route to a signer that works
     from inside the APK. See AMBER_PLUGIN below for why.
  5. Write the notification icon that capacitor.config.json names.
"""

import glob
import json
import os
import sys

MANIFEST = "android/app/src/main/AndroidManifest.xml"
ASSET_CFG = "android/app/src/main/assets/capacitor.config.json"
JAVA_ROOT = "android/app/src/main/java"
DRAWABLE = "android/app/src/main/res/drawable"

# capacitor.config.json names this icon and nothing generates it. Without it
# the plugin falls back to android.R.drawable.ic_dialog_info, so a reminder
# wears a generic system glyph instead of the app's own mark.
#
# A status bar icon is a silhouette: Android throws away the colour and keeps
# the alpha, so this is the three-bar mark drawn in flat white, with the third
# bar an outline the way the launcher icon has it.
STAT_ICON = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M2.7,4h3.6a1.2,1.2 0 0 1 1.2,1.2v13.6a1.2,1.2 0 0 1 -1.2,1.2h-3.6a1.2,1.2 0 0 1 -1.2,-1.2v-13.6a1.2,1.2 0 0 1 1.2,-1.2z" />
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M10.2,4h3.6a1.2,1.2 0 0 1 1.2,1.2v13.6a1.2,1.2 0 0 1 -1.2,1.2h-3.6a1.2,1.2 0 0 1 -1.2,-1.2v-13.6a1.2,1.2 0 0 1 1.2,-1.2z" />
    <path
        android:fillColor="#00000000"
        android:strokeColor="#FFFFFFFF"
        android:strokeWidth="1.2"
        android:pathData="M18.3,4.6h2.4a1.2,1.2 0 0 1 1.2,1.2v12.4a1.2,1.2 0 0 1 -1.2,1.2h-2.4a1.2,1.2 0 0 1 -1.2,-1.2v-12.4a1.2,1.2 0 0 1 1.2,-1.2z" />
</vector>
"""

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


AMBER_PLUGIN = '''package {pkg};

/* A NIP-55 signer, the way NIP-55 says to talk to one from an Android app.
 *
 * Written by scripts/patch-android.py. Editing it here does nothing -- edit
 * the template in that script.
 *
 * Why this exists at all: Capacitor's Bridge.launchIntent is two lines,
 *
 *     Intent openIntent = new Intent(Intent.ACTION_VIEW, url);
 *     getContext().startActivity(openIntent);
 *
 * which sets no Browser.EXTRA_APPLICATION_ID and never calls Intent.parseUri.
 * Amber decides how to read a request by whether that extra is present: with
 * it, it parses the nostrsigner: URL; without it, it reads type, pubkey and
 * the rest from intent extras. So a nostrsigner: URL sent from the WebView
 * arrives in the extras branch with no extras at all, and Amber rejects it as
 * a malformed request. An intent: URL fares worse -- its scheme is literally
 * "intent", nothing on the device claims it, and startActivity throws.
 *
 * Filling in the extras ourselves is the flow NIP-55 specifies for Android
 * apps, and it depends on none of that: no EXTRA_APPLICATION_ID, no callback
 * URL, no deep link, no clipboard. The answer comes back on the activity
 * result, which is what activity results are for.
 */

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;

import androidx.activity.result.ActivityResult;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.ActivityCallback;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.util.Iterator;

@CapacitorPlugin(name = "Amber")
public class AmberPlugin extends Plugin {{

    @PluginMethod
    public void request(PluginCall call) {{
        String type = call.getString("type");
        if (type == null || type.isEmpty()) {{
            call.reject("no-type");
            return;
        }}

        String payload = call.getString("payload", "");
        Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse("nostrsigner:" + payload));

        /* No package on sign-in, so Android offers a chooser and any NIP-55
         * signer can answer. The one that does tells us its package, and
         * every later call is pinned to it so nothing asks again. */
        String pkg = call.getString("pkg", "");
        if (pkg != null && !pkg.isEmpty()) {{
            intent.setPackage(pkg);
        }}

        intent.putExtra("type", type);
        JSObject extras = call.getObject("extras");
        if (extras != null) {{
            Iterator<String> keys = extras.keys();
            while (keys.hasNext()) {{
                String key = keys.next();
                String value = extras.getString(key);
                if (value != null) {{
                    intent.putExtra(key, value);
                }}
            }}
        }}

        try {{
            startActivityForResult(call, intent, "onSignerResult");
        }} catch (ActivityNotFoundException e) {{
            call.reject("no-signer");
        }}
    }}

    @ActivityCallback
    private void onSignerResult(PluginCall call, ActivityResult result) {{
        if (call == null) {{
            return;
        }}

        Intent data = result.getData();
        if (result.getResultCode() != Activity.RESULT_OK || data == null) {{
            call.reject("cancelled");
            return;
        }}

        /* Signers differ on whether "rejected" is a boolean extra or the
         * string "true", so accept either rather than sign something the
         * person said no to. */
        if (data.getBooleanExtra("rejected", false)
                || "true".equalsIgnoreCase(data.getStringExtra("rejected"))) {{
            call.reject("rejected");
            return;
        }}

        JSObject out = new JSObject();
        out.put("result", data.getStringExtra("result"));
        out.put("event", data.getStringExtra("event"));
        out.put("pkg", data.getStringExtra("package"));
        out.put("id", data.getStringExtra("id"));
        call.resolve(out);
    }}
}}
'''

MAIN_ACTIVITY = '''package {pkg};

/* Written by scripts/patch-android.py. Capacitor's own version of this file is
 * the same six lines without the registerPlugin, so replacing it wholesale is
 * safe and stays idempotent. */

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {{

    @Override
    public void onCreate(Bundle savedInstanceState) {{
        registerPlugin(AmberPlugin.class);
        super.onCreate(savedInstanceState);
    }}
}}
'''


def find_app_package():
    """The directory Capacitor put MainActivity in, and its package name."""
    hits = glob.glob(os.path.join(JAVA_ROOT, "**", "MainActivity.*"), recursive=True)
    if not hits:
        sys.exit(
            f"Could not find MainActivity under {JAVA_ROOT} — did `npx cap add android` run?"
        )
    folder = os.path.dirname(hits[0])
    pkg = os.path.relpath(folder, JAVA_ROOT).replace(os.sep, ".")
    return folder, pkg, hits


def patch_plugin():
    folder, pkg, existing = find_app_package()

    # Capacitor 6 writes MainActivity.java; if a template ever writes Kotlin
    # instead, drop it rather than leaving two classes with the same name.
    for path in existing:
        if not path.endswith("MainActivity.java"):
            os.remove(path)

    for name, template in (
        ("AmberPlugin.java", AMBER_PLUGIN),
        ("MainActivity.java", MAIN_ACTIVITY),
    ):
        open(os.path.join(folder, name), "w", encoding="utf-8").write(
            template.format(pkg=pkg)
        )

    print(f"Plugin: AmberPlugin + MainActivity written into {pkg}")


def patch_icon():
    os.makedirs(DRAWABLE, exist_ok=True)
    open(os.path.join(DRAWABLE, "ic_stat_icon.xml"), "w", encoding="utf-8").write(
        STAT_ICON
    )
    print("Icon: ic_stat_icon written")


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
    patch_plugin()
    patch_icon()
    patch_config()
