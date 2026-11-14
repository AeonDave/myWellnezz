# myWellnezz

A terminal app for viewing and booking gym classes at fitness centers that use
MyWellness. Manage saved accounts, choose a gym, search its classes and queue a
booking without juggling console prompts.

**Windows users:** download `myWellnezz.exe` from the
[latest release](https://github.com/AeonDave/myWellnezz/releases/latest).
The Windows x64 executable does not require a separate Python installation.

> [!NOTE]
> This is an independent, unofficial client, not affiliated with Technogym or
> MyWellness. Service compatibility can change. Offline tests do not establish
> that a live booking will succeed; check the final booking state with your gym.

## Features

- Compact [Textual](https://textual.textualize.io/) interface with keyboard and
  mouse navigation, designed for terminals of at least **80 columns × 24 rows**.
- Separate account and gym selection, with visible actions and confirmation
  before removing an account or cancelling a booked class.
- Search classes by name, teacher or room. View start/end times, booking opening
  time, free places and booking status in the selected-class details.
- Queue a booking for a future opening or a full class, cancel a queued action,
  and refresh the calendar without losing the selected class.
- Background requests, refresh countdown and visible error feedback. A queued
  request is not presented as a completed booking.
- Passwords and session tokens stored in the operating system's credential vault,
  with best-effort migration of the old local configuration.

## Installation

### Windows executable

1. Download `myWellnezz.exe` from [Releases](https://github.com/AeonDave/myWellnezz/releases).
2. Run it in Windows Terminal or a regular console window. Keep the terminal open
   while booking actions are queued.
3. Choose **Add**, sign in with your MyWellness account, then open an account and gym.

The release also provides `SHA256SUMS` for checking the downloaded file. In PowerShell:

```powershell
Get-FileHash .\myWellnezz.exe -Algorithm SHA256
```

Compare the resulting hash with the entry in `SHA256SUMS`.

### Run with Poetry

Requires Python **>=3.11,<3.16**, Poetry and a usable OS credential-vault backend.

```console
git clone https://github.com/AeonDave/myWellnezz.git
cd myWellnezz
poetry install
poetry run mywellnezz
```

### Run Manual

From the cloned repository, create and activate a virtual environment.

**Windows PowerShell:**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install .
python -m mywellnezz.main
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
python -m mywellnezz.main
```

macOS uses Keychain. Linux requires a working keyring backend, such as a
Secret Service-compatible desktop service; a headless environment may not
provide one. Only the Windows x64 executable is provided in the release.

## Usage

### Interface controls

The account menu contains saved accounts only. Use **Open**, **Add**, **Remove**
or **Quit**. `Enter` opens the selected account, `a` adds an account, `d` removes
one with confirmation, and `q` quits. A gym picker appears when the account has
more than one gym; use **Open gym**, **Back** or **Quit**.

On the dashboard, select a class with the arrow keys or mouse. Click the search
field, or use `Tab` to focus it, to filter by class, teacher or room. Shortcuts
apply outside text-entry fields; use `Tab` to return to the table or buttons.

| Key | Dashboard action |
| --- | --- |
| `↑` / `↓` or mouse | Select a class |
| `Enter` on a class / `b` | Book, cancel a queued action, or request an unbook |
| `r` | Reload classes |
| `Esc` | Return to the account menu |
| `q` | Quit |

The primary button changes to **Book**, **Book when available**, **Cancel queued**
or **Unbook** as appropriate. Existing participation must be confirmed before
unbooking. Waiting-list entries retain the service's existing queue/rebooking
behavior; they are not presented as cancellable participation.

Leaving a dashboard with queued booking actions asks before cancelling them.
**Cancel queued** stops this app's pending task; it does not undo a request that
has already reached the service. Check the refreshed participation state before
assuming a booking or cancellation has completed. Gym logo art is not loaded by default.

## Configuration and security (v2)

- Non-secret account/profile data lives in the user configuration directory,
  resolved with [platformdirs](https://pypi.org/project/platformdirs/):
  `%LOCALAPPDATA%\myWellnezz\config.json` on Windows. It does not depend on the
  working directory, so the executable can be launched from another folder.
- Passwords and session tokens use [keyring](https://pypi.org/project/keyring/):
  Windows Credential Manager, macOS Keychain or the configured Linux backend.
  They are not written to the new JSON configuration.
- On first start without a new configuration, a legacy `conf.json` is imported
  if its MAC-derived obfuscation key still matches. After a successful import,
  the app attempts to rename it to `conf.json.migrated.bak`; it is not deleted.
  If it cannot be decoded, the file is left untouched and you sign in again.
- Legacy files and backups can still contain recoverable credentials. Keep them
  private; do not attach them to issues or commit them to Git.

If the credential vault is unavailable, restore access to that OS service before
retrying. Do not work around it by putting your password in the configuration.

## Development and packaging

Install the development dependencies with `poetry install`, then run:

```console
poetry run python -m pytest -q
poetry run python -m ruff check .
poetry check
```

The tests use offline service boundaries and Textual Pilot, including virtual
80×24 and 120×40 terminals. They do not access your real vault or book live classes.
The latest local checks used Python 3.14.6 and Textual 8.2.8; other supported
Python versions and real-terminal behavior need their own runtime checks.

### Create binary

Build the Windows executable on Windows:

```console
poetry run build
```

The output is `dist/myWellnezz.exe`. The build bundles Textual's dynamic modules
and resources plus keyring's backends, uses an isolated `build/pyinstaller/`
workspace, and preserves unrelated files in `build/` and `dist/`. Rebuilding
replaces the executable with the same name.

To create Python wheel and source packages instead:

```console
poetry build
```

See [the modernization review](docs/modernization.md) for the comparison with the
last tagged release, architecture decisions, regression fixes and verification
limits. Issues and focused pull requests are welcome.

Licensed under [Apache-2.0](LICENSE).
