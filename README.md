# Groundwork

Home strength training for people who don't like gyms. Bodyweight plus a pair of weights, three sessions a week, with a daily check-in that keeps the habit alive on rest days.

The whole app is one file: `www/index.html`. No build step, no framework, no bundler. Edit it in any text editor, commit, and CI produces an APK.

## Nostr

Optional, and off until you sign in. Four ways in, under **You → Nostr account**:

- **Amber** (NIP-55). The main path on Android, and only offered on Android. The app hands Amber a request over a `nostrsigner:` link and Amber replies on a `groundwork://` link. Your private key never enters this app.
- **Bunker** (NIP-46). Paste the `bunker://` address from nsecBunker, nsec.app, Amber's bunker mode or similar. Your key stays in the signer and every signature is a round trip over a relay — so this is the one route that works everywhere, desktop included.
- **Browser extension** (NIP-07). Only appears if `window.nostr` exists, so it's for desktop browsers, not the APK.
- **npub, read-only**. Restores a backup, can't make one.

#### A note on the Amber link

The first release built Chrome's `intent:…#Intent;scheme=nostrsigner;…;end` URL. That works in Chrome for Android and nowhere else — and specifically not in the APK, where Capacitor hands an unknown scheme to `new Intent(ACTION_VIEW, Uri.parse(url))`. The scheme of an `intent:` URL is literally `intent`, nothing claims it, and the tap did nothing at all. It now builds a plain NIP-55 `nostrsigner:` URI.

Two things went with it. The `groundwork://` deep link that `scripts/patch-android.py` has always registered is finally listened for, so answers come back over the link rather than by scraping the clipboard — which needed a secure context, a permission prompt, and the page surviving the trip. And if nothing takes the intent, the app says so in about four seconds instead of sitting silent for two minutes.

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

### The board

A leaderboard, under **Social → Board**, with two scopes: everyone the relays return, and just the people you have added.

It ranks on **days you turned up in the last thirty**, and nothing else. No weights, no reps, no volume — the same constraint the rest of the Social tab has always had, for the same reason. A beginner and a veteran who both trained three times this week are level, because they are.

Two rules do the work:

- **One session a day counts once.** Training twice on a Tuesday beats nobody, and publishing the same session twenty times buys nothing. Weeks on target are counted from days for the same reason.
- **Two separate days to appear at all**, which keeps out the long tail of people who published once and vanished.

The global scope is the only query in the app with no `authors` filter — `kind 1301` over the last thirty days, whatever your relays feel like returning. Names are looked up for the top 25 only, so scrolling does not cause a fetch storm.

What it cannot do, and says on the screen rather than implying otherwise: none of it is verified. Anyone can publish a workout record they did not earn. It only ever sees people who have public publishing switched on, which most people leave off, and it is whatever your relays hold rather than the whole world. It is a nudge, not a record.

### Zaps

You can send someone sats from the Social tab — feed rows, the People list, your partner, and the board. It follows NIP-57, so the zap shows up in every other nostr client too, not only here.

Each zap is three steps, and the sheet says so rather than appearing to hang: the recipient's lightning address is fetched for an invoice, Amber signs the `kind 9734` request, and Spark pays it.

It degrades rather than failing silently. No lightning address in their profile and it says so. An old-style `lud06` LNURL and it says it cannot read one. A server that does not do nostr and it still pays, labelled a tip rather than a public zap — and Amber is not asked for a signature that would only be thrown away.

**The invoice amount is checked against what you agreed before anything is paid.** If their server returns an invoice for a different number, nothing is sent and the screen says what happened.

This is the first thing in the app that makes an HTTPS request. Everything else is a WebSocket to a relay you chose; a zap fetches a URL built out of a stranger's profile. So it will only fetch an ordinary public https host — no bare IP addresses, no ports or credentials, nothing resolving inside whatever network the phone is on — with a timeout and a ceiling on how much it will read. Routing fees are capped, and anything over 5,000 sats asks twice.

### The wallet

**You → Wallet** sets up a [Spark](https://spark.money) wallet on the device. Balance, receive by invoice, send, a default zap amount, and the twelve words.

Sending takes three things and works out which is which from what you paste: a bolt11 invoice, a lightning address like `name@example.com`, or a Spark `sp1…` address. It reuses the zap path's checks, so it refuses exactly what a zap refuses — https only, no IP literals or private hosts, and the invoice amount verified against what you agreed before anything moves. An invoice with no amount on it is refused rather than quietly turned into a box asking how much, which is a different thing from what you pasted. Paying a lightning address here sends no zap request, so it is a private payment rather than something published to nostr.

It is a tips wallet and the app says so everywhere it can. The keys live in this app's storage, which Android may clear when space runs short.

That is survivable because of the backup, and only because of it: the recovery phrase is NIP-44 encrypted to your own nostr key by Amber and published as a `kind 30078` event with the `d` tag `groundwork-wallet-v1` — the same mechanism as the workout backup. Reinstall, sign in with Amber, and the wallet comes back with nothing to write down.

The honest costs, which the screen states rather than buries:

- Your sats now ride on your nostr key. Whoever gets your nsec gets the wallet.
- And on a relay keeping one event. If every relay drops it and the device is wiped, it is gone.
- A read-only npub sign-in cannot decrypt, so it cannot spend.

So the twelve words are also shown, for anyone who wants paper. They are **excluded from the file export**, which is plain JSON headed for the Downloads folder, and an imported file can never install a wallet.

Worth knowing: `SparkWallet.initialize()` authenticates with Spark's operators, so the wallet needs a connection every time it opens. There is no offline balance.

#### The two generated files

Everything else in the repo is hand-edited. These are not:

| | size | needed by |
|---|---|---|
| `www/nostr.js` | ~100 KB | bunker (NIP-46) sign-in |
| `www/spark.js` | ~6 MB | the zapping wallet |

`spark.js` is roughly twenty times the size of the rest of the app, because two WASM blobs are inlined as base64. Neither file is precached by the service worker or loaded at startup: each is fetched the first time it is actually wanted and cached from then on, so anyone who never zaps never downloads six megabytes, and anyone who never uses a bunker never downloads the other.

To move to newer versions:

```
./scripts/build-vendor.sh                 # both
./scripts/build-vendor.sh nostr           # just one
SPARK_VERSION=0.13.0 ./scripts/build-vendor.sh spark
```

Then bump `CACHE` in `www/sw.js` and commit the result. Editing `index.html` by hand still needs no build step of any kind.

### Relays

Four defaults, editable under **You → Nostr account → Relays**. One `wss://` relay is the minimum.

### What needs a real device

Amber is an Android app, so NIP-55 only works in the installed APK — not in a browser, and the button is not offered in one. Relay connections are WebSockets, which a browser preview's security policy will also block. Build the APK to test any of this.

Bunker sign-in is the exception: it is relays all the way down, so it works in a browser as well as the APK. If Amber ever misbehaves, that is the route that does not depend on an Android intent surviving a WebView.

## Repo layout

```
www/index.html                    the entire app
capacitor.config.json             app id, name, notification icon
package.json                      Capacitor + plugins
www/manifest.webmanifest          makes it installable from a browser
www/nostr.js                      nostr-tools, bundled — for bunker sign-in
www/spark.js                      the Spark SDK, bundled — for the wallet
scripts/build-vendor.sh           regenerates both; nothing else needs a build
www/sw.js                         offline support
www/icon-*.png                    app icons
scripts/patch-android.py          permissions, deep link, signer visibility
.github/workflows/android.yml     builds the APK
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
- `YOGA` / `YOGA_POSES` / `SIT` — the flows, the poses they are built from, and the meditation sessions
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

## Everything else you do

The **Anything else today?** card on Today covers the things that are not lifting. None of it counts towards your weekly strength sessions — different job — but all of it holds the day streak.

### Jogs and rides

Start the clock and it keeps time while you are out, or type the minutes in afterwards as before. At the end it asks for a distance and works out your pace: minutes per kilometre for a jog, km/h for a ride. Leave the distance blank and it just logs the time.

**No location is used and none is requested.** The app never touches geolocation, so there is no permission prompt to refuse, and a test asserts that stays true by replacing `navigator.geolocation` with something that throws. Distance is a number you type, which is what a treadmill, a bike computer or a map you looked at afterwards gives you anyway.

The clock is *computed* from `Date.now()` rather than counted. Every other timer in the app decrements a counter once a second, which is fine for a thirty-second stretch and would be badly wrong here: a backgrounded WebView throttles timers to roughly one a minute, so a counted clock would come back from a half-hour run claiming four minutes. The interval only repaints; the number it paints is arithmetic on wall-clock time. A run in progress is written to storage as it goes, so a WebView killed while your phone was in a pocket does not take the run with it — Today offers to pick it back up, finish it, or throw it away.

### Yoga

Three flows, guided the way a workout is — a figure, a clock, and a sentence telling you what to do with your body:

- **Loosen up**, about eight minutes. Spine and hips, good on a rest day.
- **Full body**, about twenty. Standing work first, floor work after.
- **Wind down**, about twelve. Floor-based and slow, for the evening.

Twelve poses shared between them, so a pose is drawn once and appears wherever it belongs; three more come from the cooldown stretches rather than being redrawn. The player is the cooldown stretch player — a yoga pose and a cooldown stretch are the same shape of thing, so the same code renders either.

It is not a yoga class. It is a sequence of held positions with a timer, which is the part an app can usefully do.

### Meditation

Three guided sessions — **breath focus**, **body scan** and **wind down** — as timed steps with something to read at the top of each. No figure: a stick figure sitting still for four minutes helps nobody.

And a plain timer with a bell, because some people want silence and an app insisting on talking them through it is the opposite of the point.

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

**One workflow, deliberately.** GitHub offers a "Deploy static content to Pages" starter that publishes the whole repo, and for a while this repo had both it and `pages.yml`. They share a concurrency group and trigger on the same push, so every deploy was a race between serving the app at the site root and serving it under `/www/` — which changes the service worker's scope and the manifest's `start_url`, and quietly breaks installed copies. If Pages ever starts behaving strangely, check there is still only one workflow deploying it.

## iPhone

There is no iOS build and there is not going to be one. Two targets get looked after: the **Android APK** and the **web app**. On an iPhone, the web app is the answer.

Open the page in Safari, tap Share, then **Add to Home Screen**. It installs as a proper app — own icon, no browser chrome, works offline, storage kept separately from Safari's.

### Why no native iOS

The native build never earned its keep. It bought exactly one thing the web app does not have — local notifications — and cost a macOS runner at ten times Linux rates for an unsigned `.ipa` that Apple expires after seven days when re-signed with a free account. That is not a distribution channel, it is a weekly chore.

Bunker sign-in closed the other gap. Nostr on iOS used to mean pasting an npub and living read-only, because Amber is Android-only. A NIP-46 bunker works anywhere there is a relay, so an iPhone on the web app now gets the whole thing: encrypted backup, publishing, the board, zaps.

### What an iPhone still misses

- **The daily reminder.** iOS does not let home-screen web apps schedule local notifications, and no amount of code gets around it. The reminder screen says so and suggests a repeating phone alarm, which does the same job.
- **Durable storage.** This is the one that bites. Safari clears web app storage after about seven days without opening it. Your history, your streak and — if you set one up — your wallet all live in that storage.

  So on an iPhone, signing in for the encrypted backup is not a nice-to-have. Open the app once a week and it never comes up; leave it a fortnight without a backup and you may come back to an empty app.

## Releasing properly

The workflow builds a *debug* APK. It installs and runs fine, but it's signed with a throwaway debug key, so you can't ship it to the Play Store and you can't upgrade over it with a differently-signed build.

For a real release you need a keystore, stored as GitHub secrets, and `assembleRelease` in place of `assembleDebug`. Worth doing once the app has settled down — not before.
