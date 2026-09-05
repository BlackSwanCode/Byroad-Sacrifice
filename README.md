# ⚡ Byron — MCP & API Security Scanner

> **RetroWave Edition** — APIs and MCP servers security scanner

Byron is a Python security testing tool designed to audit REST APIs, GraphQL endpoints, and MCP (Model Context Protocol) servers. It ships in two flavours: a command-line engine (`Byron5a.py`) and a full graphical interface (`ByronTK.py`) with a RetroWave aesthetic built on Tkinter.

---

## 📁 Repository Structure

```
Byron/
├── Byron5a.py        # Core scanning engine (SecurityTester, AggressionLevel, ApiType)
├── ByronTK.py        # Tkinter GUI frontend — RetroWave Scanner
├── endpoints.txt     # Sample endpoint list for REST/GraphQL scans
├── payloads.lst      # Payload list used during security tests
└── payloads/         # Directory of additional payload files
```

---

## ✨ Features

- **Multi-protocol support** — REST, GraphQL, Generic APIs, and MCP servers (Mossbauer mode)
- **Adjustable aggression levels** — `low`, `medium`, or `high` (controls request delay and payload count)
- **Proxy support** — route traffic through a local proxy (e.g. Burp Suite, mitmproxy)
- **Authentication** — Bearer token, username/password
- **Taurus tests** — optional extended test suite
- **Graphical interface** — `ByronTK.py` provides a RetroWave-themed GUI with:
  - Live log console (thread-safe, ANSI-stripped)
  - JSON config loader
  - File picker for endpoints
  - Start / Abort scan controls
- **Colour-coded log output** — warnings in yellow, errors in red, MCP events in magenta

---

## 🚀 Getting Started

### Prerequisites

- Python 3.8+
- `tkinter` (included with most Python distributions)

### Installation

```bash
git clone https://github.com/doktornand/Byron.git
cd Byron
pip install -r requirements.txt   # if a requirements file is added
```

### Run the GUI

```bash
python ByronTK.py
```

### Run the CLI engine directly

```bash
python Byron5a.py \
  --target https://api.example.com \
  --api-type rest \
  --endpoints endpoints.txt \
  --aggression medium
```

---

## ⚙️ Configuration

All options can be set through the GUI or passed as arguments to the CLI. A JSON config file can also be loaded in the GUI via **📂 Load JSON Config**.

| Option | Description | Default |
|---|---|---|
| `--target` | Target base URL | — |
| `--api-type` | `rest`, `graphql`, `generic`, `mossbauer` | `rest` |
| `--aggression` | `low` / `medium` / `high` | `medium` |
| `--endpoints` | Path to endpoints file | — |
| `--proxy-host` | Proxy hostname | `192.168.1.20` |
| `--proxy-port` | Proxy port | `8118` |
| `--auth-token` | Bearer token | — |
| `--username` | Username for auth | — |
| `--password` | Password for auth | — |
| `--taurus` | Enable Taurus extended tests | `false` |

### Aggression levels

| Level | Request delay | Payload count |
|---|---|---|
| `low` | 2.0 s | 3 |
| `medium` | 1.0 s | 5 |
| `high` | 0.5 s | all |

---

## 🔌 API Types

| Mode | Description |
|---|---|
| `rest` | Standard REST API scanning using the endpoints file |
| `graphql` | GraphQL introspection and query fuzzing |
| `generic` | Generic HTTP endpoint scanner |
| `mossbauer` | MCP server scanning — no endpoints file required |

---

## 📋 Payload & Endpoint Files

- **`endpoints.txt`** — one endpoint path per line (e.g. `/api/v1/users`)
- **`payloads.lst`** — one payload per line, injected during fuzz testing
- **`payloads/`** — directory for additional categorised payload files

---

## ⚠️ Legal Disclaimer

Byron is intended for **authorised security testing only**. Always obtain explicit written permission before scanning any system or API you do not own. Misuse of this tool may violate local laws and regulations. The author accepts no liability for unauthorised use.

---

## 🛠️ Development Notes

- `ByronTK.py` imports `SecurityTester`, `AggressionLevel`, and `ApiType` from `Byron5a.py`. Both files must be in the same directory.
- The GUI uses a thread-safe queue-based logging handler to display scan output without blocking the UI.
- A minor patch in `ByronTK.py` backfills `get_request_delay` and `get_payload_count` methods on `AggressionLevel` if they are missing from the core module.

---

## 📄 License

This project does not currently specify a license. Please contact the author before redistributing or modifying.

---

*Made with 💜 and neon lights by [doktornand](https://github.com/doktornand)*
