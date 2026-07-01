# How to use JARVIS

JARVIS runs on your Mac. It remembers your conversation, searches the web,
reads files, reports system status, **opens and controls apps**, and — in the
Console — **listens, speaks, and wakes on two claps**. It becomes much smarter
the moment you add a Claude API key.

---

## Start it — the Console (voice + visual UI) ⭐

In Finder, open the `jarvis-os` folder and **double-click `Launch JARVIS Console.command`**.
Your browser opens with the JARVIS interface.

- **Allow the microphone** when the browser asks.
- Press the **🎙 mic** (or click the glowing orb) and **speak** — JARVIS talks back.
- Flip on **Two-clap wake**, then **clap twice** to summon JARVIS hands-free.
- Or just type in the box.

> Voice needs **Chrome or Safari**. First launch, macOS may say the `.command`
> file is from an unidentified developer → right-click it → **Open** → **Open** (once).

## Or the terminal (text only)

```bash
cd ~/Desktop/Claude\ Jarvis/jarvis-os
./jarvis chat        # talk to JARVIS in the terminal
./jarvis console     # same as the Console launcher
./jarvis health      # check that everything is wired up
```

---

## What you can say

| You type | JARVIS does |
|---|---|
| `hello` / anything | Chats (smart once you add a key — see below) |
| `search for the tallest mountain` | Web search (DuckDuckGo + Wikipedia, no key needed) |
| `what time is it` | Tells you the local date and time |
| `system status` | Reports CPU, memory, and disk usage |
| `list files in ~/Downloads` | Lists a folder's contents |
| `read file notes.txt` | Reads a text file (your credential folders are blocked) |
| `launch Spotify` | Opens an app |
| `open website apple.com` | Opens a site in your browser |
| `what did I say?` | Recalls earlier in the conversation |

Everything above works **offline**, with no API key.

**Controlling apps** (typing, clicking, editing inside other apps via AppleScript)
needs one permission: the first time, macOS asks to allow *Terminal* (or your
browser) to control that app — click **OK**. Opening apps and websites needs nothing.

---

## Make it smart (add Claude)

By default JARVIS replies with simple built-in responses. To make it actually
reason and hold a real conversation:

1. Get a key at <https://console.anthropic.com> → **API Keys** → **Create Key**.
2. Open the `.env` file in the `jarvis-os` folder and paste your key:
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   ```
3. Relaunch JARVIS. It detects the key and switches to live Claude automatically —
   no other changes needed. (The "Offline mode" notice disappears when it's live.)

Your key stays on your Mac, in your `.env` file.

---

## Good to know

- **Memory** persists between sessions in `data/memory/long_term/conversations.db`.
- **Safety:** file reads are blocked from `~/.ssh`, `~/.aws`, `~/.gnupg`, and system folders.
- **What's not here yet:** voice ("Hey JARVIS") and the desktop window. Those need
  extra system libraries and a fuller setup; the text brain above is the working core.
