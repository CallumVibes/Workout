# Groundwork

Home strength training for people who don't like gyms. Bodyweight plus a pair of weights, three sessions a week, with a daily check-in that keeps the habit alive on rest days.

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

The **Friends** tab reads your friends' published workout records and shows how often they have trained. Add people by npub, or import your nostr follow list in one tap. The friends list is local to this device and does not touch your real nostr follows.

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
www/manifest.webmanifest          makes it installable from a browser
www/sw.js                         offline support
www/icon-*.png                    app icons
scripts/patch-android.py          permissions, deep link, signer visibility
.github/workflows/android.yml     builds the APK
.github/workflows/ios.yml         builds an unsigned .ipa on a Mac runner
.github/workflows/pages.yml       publishes www/ to GitHub Pages
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

- `EX` — the twenty-eight exercises, their rep ranges, cues, mistakes and difficulty ladders
- `PLAN2` — the slot table: which movement pattern and muscle group each session slot is for, and which exercises may fill it
- `TIERS`, `SHAPES`, `SET_FLOOR` — the coach's dials (see **How the workout is chosen**)
- `SESSIONS` — the names and cooldowns for Session A and Session B
- `MOB` — the three rest-day mobility moves
- `LESSONS` — the daily ideas that cycle through the check-in
- `NUDGES` — the notification wording
- `BADGES` — the milestones

The colour palette lives in the `:root` block at the top of the `<style>` section.

## How the workout is chosen

Everything in the `THE COACH` block of `www/index.html`. Nothing about it is a black box on the phone either — the Today screen carries a **Why this workout** note, and **You → Coaching** shows the same reasoning in full.

### The spine stays the same

Two full-body sessions alternate. Each has five slots, six once you have some history, and every slot names both a movement *pattern* and the *muscle group* it is there to train. Candidates are filtered to both, which is less pedantic than it sounds: chair dips are a perfectly good push, so without the muscle filter a stalled push-up rotates to dips and the chest quietly gets nothing for five months while the app reports a full house. That happened in testing. A slot is a promise about what gets trained.

The first three slots are **anchors** and hold still, because progression needs the same movement week after week to mean anything. The rest rotate.

### It meets you where you are

Four tiers, worked out from your sessions, how far up the ladders you are, and — as a floor, so a returning lifter is not treated as a novice — what you said at setup. You can also just tell it, under **Coaching**.

| | when | sets | slots | to move up a rung | formats |
|---|---|---|---|---|---|
| Finding your feet | first six sessions | 3 anchor, 2 accessory | 5 | one top session | straight sets only |
| Building | 6–24 | 3 and 3 | 5 | one top session | + tempo, paired sets |
| Steady | 25–80 | 4 and 3 | 6 | two in a row | + rounds |
| Seasoned | 80+ | 4 and 3 | 6 | two in a row | + twelve-minute blocks |

### It reads every session

One number per movement per session — reps done, times the weight when there was one — compared against last time. Climbing a rung counts as progress by definition, since a harder version for fewer reps is the whole point.

A movement that has not beaten itself in a while gets three escalating nudges, none of them dramatic:

- **two sessions** — back to the bottom of the range with a four-second lowering and an extra set. A different kind of hard, not more of the same.
- **four** — the slot rotates to a different movement in the same pattern.
- **six, and going backwards** — the Today screen *offers* a rung down. It never takes one.

### It prioritises what you can see

Every muscle group has a floor of hard sets per week, and the last slot of each session goes to whatever is furthest below its floor. Compounds come first while you are fresh, rep ranges stay where size is built, and the check-in feeds back in: a night of bad sleep or a "properly sore" buys a set off the accessories rather than a skipped session.

Six weeks on target schedules an **easy week** — a set off everything, targets mid-range, no novelty. It is the week the previous six turn into something visible, and it can be waved away.

Floors bend to what your kit can reach. With nothing but a floor there is exactly one direct arm exercise in the app, which is a fact about home training rather than a fault in the programme, and the Progress screen says so rather than showing a red bar nobody can clear.

### It does not let you get bored

Accessory movements hold a slot for a few sessions and then hand over, staggered so the programme drifts rather than lurching. Occasionally the whole session comes in a different shape:

- **Slow lowering** — same sets and reps, four seconds down on every one.
- **Paired sets** — two movements on a screen, alternating, shorter rests.
- **Rounds** — three times through the whole list, one set of each. The cues and figures step aside and it becomes a checklist.
- **Twelve minutes** — four rounds against a clock. Tick what you finish.

Novelty is rationed: never twice running, never on a tired day, never in an easy week, never in your first six sessions, and straight sets stay the clear majority. The two shapes that change the reps on purpose are marked as such, and a session run in one of them sits out the progress comparison entirely — a circuit day should never read as a collapse in performance.

How much of this happens is a setting: **Steady**, **Balanced** or **Restless**, under **You → Coaching**.

### What it will never do

Move you up a rung, add weight, or drop you back down without asking. Those stay as offers on screen with two buttons. The app decides how much work you do and which movements do it; you decide how hard each one gets.

## Reminders

One notification a day at a time you choose in the app, under **You → Daily reminder**.

It skips any day you've already checked in or trained, and it reschedules every time the app is opened. On a Saturday where you're short of your weekly target, it says so instead of using the usual wording.

Reminders do nothing in a browser — they need the installed app. Android will ask for notification permission the first time you turn them on.

## Equipment

Setup asks what the person owns — nothing, weights, bands, a pull-up bar, or any combination — and the sessions are built from that. Each exercise declares the kit it needs, and each session slot is a *movement pattern* and a *muscle group* with a list of candidates. Which one wins is the coach's decision, described above.

That means a bodyweight-only user still gets a pulling exercise, which matters: without one, a home programme trains the front of the body and nothing else, and round shoulders are the result. Under-table rows and doorframe rows fill that gap; pike push-ups cover overhead pressing.

If the person says their weights are adjustable, progression changes. Instead of only climbing the variation ladder, the app offers to add weight and drop back to the bottom of the rep range — the simpler lever when you have it.

The Learn tab and the ladder editor both filter to what the person can actually do, so nobody reads a guide for kit they do not own.

## Coming back after a break

Fourteen days or more without a session and the Today screen offers to drop every exercise back a rung (two rungs after eight weeks). Nothing about your history or streaks changes. You can decline, and it will not ask again for three days.

Everything the coach had learned about your rate of progress was learned before the break, so it is thrown away at the same time rather than left to call your first session back a collapse.

## Your data

Everything is stored on the device in `localStorage`. Nothing is uploaded and there is no account.

**You → Export as a file** writes a JSON backup, and **Import a file** reads one back in. Import merges rather than overwrites: existing sessions are kept, duplicates are ignored, and ladder positions take whichever is further along — the same rules as the nostr restore. Android can also clear WebView storage when space runs low, which is rare but real — if you get attached to a long streak, worth migrating to `@capacitor/preferences`, which survives that.

## Web version

`.github/workflows/pages.yml` publishes the `www` folder to GitHub Pages on every push to `main`, so the app is served at the repo's Pages URL directly rather than under `/www/`.

This needs **Settings → Pages → Source** set to **GitHub Actions**. Left on "Deploy from a branch" it serves the repo root, where Jekyll renders this README as the homepage.

A `.nojekyll` file is added during the build so nothing gets filtered on the way out.

## iOS

Three ways to run this on an iPhone, in order of effort.

### 1. Add to Home Screen — works today, no Mac, no account

Open the page in Safari, tap Share, then **Add to Home Screen**. It installs as a proper app: own icon, no browser chrome, works offline, data kept separately from Safari.

Everything works except the daily reminder. iOS does not let home-screen web apps schedule their own local notifications, and no amount of code gets around it. The reminder screen says so rather than pretending, and suggests a repeating phone alarm at the same time, which does the same job.

Amber is Android-only, so nostr sign-in on iOS is limited to pasting an npub (read-only). A NIP-46 remote signer would fix that properly and is the right long-term answer.

### 2. Native build, sideloaded

`.github/workflows/ios.yml` builds an unsigned `.ipa` on a macOS runner. Run it from the Actions tab — it is deliberately not on the push trigger, because macOS minutes cost roughly ten times what Linux ones do on private repos.

The output is unsigned, so it will not install by itself. Tools like AltStore or Sideloadly re-sign it with a free Apple ID and install it over USB. Apps signed with a free account expire after seven days and need refreshing.

This version does get local notifications, because it is a real app rather than a web page.

### 3. App Store

Needs an Apple Developer account at £79 a year, a signing certificate and provisioning profile stored as repo secrets, and review. Only worth it if other people are going to use this.

### What differs on iOS

- **Reminders**: home-screen app no, native build yes
- **Amber sign-in**: no — Android only. npub read-only works, NIP-46 would be the fix
- **Relay connections**: fine in both
- **Storage**: iOS clears web app storage after about seven days of not opening it, so export or sign in for backup matters more here than on Android

## Releasing properly

The workflow builds a *debug* APK. It installs and runs fine, but it's signed with a throwaway debug key, so you can't ship it to the Play Store and you can't upgrade over it with a differently-signed build.

For a real release you need a keystore, stored as GitHub secrets, and `assembleRelease` in place of `assembleDebug`. Worth doing once the app has settled down — not before.
