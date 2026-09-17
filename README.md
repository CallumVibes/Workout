# Groundwork

Home strength training for people who don't like gyms. Bodyweight plus one pair of dumbbells, three sessions a week, with a daily check-in that keeps the habit alive on rest days.

The whole app is one file: `www/index.html`. No build step, no framework, no bundler. Edit it in any text editor, commit, and CI produces an APK.

## Nostr

Optional, and off until you sign in. Three ways in, under **You → Nostr account**:

- **Amber** (NIP-55). The main path on Android. The app hands Amber a request over a `nostrsigner:` link and Amber replies on a `groundwork://` link. Your private key never enters this app.
- **Browser extension** (NIP-07). Only appears if `window.nostr` exists, so it's for desktop browsers, not the APK.
- **npub, read-only**. Restores a backup, can't make one.

### Encrypted backup

Signing in with Amber or an extension gives you a backup that fixes the uninstall problem. Your whole history — sessions, check-ins, ladder positions, settings — is encrypted to your own key with NIP-44 before it leaves the device, then published as a NIP-78 app-data event (`kind 30078`, `d` tag `groundwork-v1`) to your relays.

Only you can decrypt it. Relay operators see an opaque blob.

Restore merges rather than overwrites: sessions already on the device are kept, anything the backup has that the device doesn't is added, and ladder positions take whichever is further along. So restoring onto a phone that's already been used is safe.

Backup runs automatically after each session and check-in if the toggle is on, silently and in the background. Failures are quiet by design — a relay being down should not interrupt a workout.

### Public workout records

Off by default, and clearly labelled as unencrypted. When on, each finished session publishes a `kind 1301` workout record following the NIP-101e draft, for interoperability with other nostr fitness clients.

That draft is not final and the tag structure may change. If interop matters to you, check the current spec before relying on it.

Milestones also get a **Share on nostr** button, which drafts a `kind 1` note you can edit before it goes anywhere.

### Crew and challenges

The **Crew** tab reads your friends' published workout records and shows how often they have trained. Add people by npub, or import your nostr follow list in one tap. The crew list is local to this device and does not touch your real nostr follows.

A deliberate constraint: this screen never shows weights or reps, only frequency. Beginners lose every comparison against experienced lifters, and beginners are exactly the people who most need to keep going. Turning up three times a week looks identical whoever you are.

Challenges are shared targets over a fixed number of days. The challenge itself is a `kind 30078` event tagged `groundwork-challenge`, joining publishes one tagged `groundwork-join`, and the leaderboard is computed client-side from each participant's `kind 1301` records inside the window. No server, no coordinator.

The catch is that it only works for people who have public workout publishing switched on. Anyone with it off looks inactive even if they are training every day, and the screen says so rather than leaving you guessing.

Cheering someone publishes a `kind 7` reaction to their most recent workout.

### Relays

Four defaults, editable under **You → Nostr account → Relays**. One `wss://` relay is the minimum.

### What needs a real device

Amber is an Android app, so NIP-55 only works in the installed APK — not in a browser. Relay connections are WebSockets, which a browser preview's security policy will also block. Build the APK to test any of this.

## Repo layout

```
www/index.html                    the entire app
capacitor.config.json             app id, name, notification icon
package.json                      Capacitor + plugins
scripts/patch-android.py          permissions, deep link, signer visibility
.github/workflows/android.yml     builds the APK
```

The `android/` folder is deliberately **not** committed. CI generates it on every run, which means you never need Android Studio or a desktop machine.

## Getting an APK

1. Push this folder to a new GitHub repo, on the `main` branch.
2. Open the **Actions** tab. The build starts on its own, or press **Run workflow**.
3. Wait five to ten minutes. The first run is slowest — Gradle is downloading everything.
4. Open the finished run and download **groundwork-apk** from the Artifacts section.
5. Unzip it on your phone and open the `.apk`. Android will ask you to allow installs from that source; that's expected for an app that hasn't come from the Play Store.

## Changing the app

Edit `www/index.html` and push. Everything you'd want to adjust is near the top of the `<script>` block:

- `EX` — the ten exercises, their rep ranges, cues, mistakes and difficulty ladders
- `SESSIONS` — which exercises land in Session A and Session B
- `MOB` — the three rest-day mobility moves
- `LESSONS` — the daily ideas that cycle through the check-in
- `NUDGES` — the notification wording
- `BADGES` — the milestones

The colour palette lives in the `:root` block at the top of the `<style>` section.

## Reminders

One notification a day at a time you choose in the app, under **You → Daily reminder**.

It skips any day you've already checked in or trained, and it reschedules every time the app is opened. On a Saturday where you're short of your weekly target, it says so instead of using the usual wording.

Reminders do nothing in a browser — they need the installed app. Android will ask for notification permission the first time you turn them on.

## Coming back after a break

Fourteen days or more without a session and the Today screen offers to drop every exercise back a rung (two rungs after eight weeks). Nothing about your history or streaks changes. You can decline, and it will not ask again for three days.

## Your data

Everything is stored on the device in `localStorage`. Nothing is uploaded and there is no account.

**You → Export as a file** writes a JSON backup, and **Import a file** reads one back in. Import merges rather than overwrites: existing sessions are kept, duplicates are ignored, and ladder positions take whichever is further along — the same rules as the nostr restore. Android can also clear WebView storage when space runs low, which is rare but real — if you get attached to a long streak, worth migrating to `@capacitor/preferences`, which survives that.

## Releasing properly

The workflow builds a *debug* APK. It installs and runs fine, but it's signed with a throwaway debug key, so you can't ship it to the Play Store and you can't upgrade over it with a differently-signed build.

For a real release you need a keystore, stored as GitHub secrets, and `assembleRelease` in place of `assembleDebug`. Worth doing once the app has settled down — not before.
