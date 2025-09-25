# Ramener PDF Renamer

Python utility that extracts metadata from PDF reports using the `qwen-flash` model and renames files following `YYYY-MM-DD_Source_Title.pdf`. It targets macOS Finder Quick Action integration so you can right-click a PDF and trigger the workflow.

## Requirements

- macOS with Python 3.10+
- Aliyun Bailian API key with access to `qwen-flash`

Set up a virtual environment and install the package:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Export the API key (or keep it in a config file):

```bash
export RAMENER_API_KEY="sk-..."
```

Or create `~/.config/ramener/api_key` so the Quick Action can read the key without extra environment setup:

```bash
mkdir -p ~/.config/ramener
printf "sk-..." > ~/.config/ramener/api_key
chmod 600 ~/.config/ramener/api_key
```

Optional environment overrides:

- `RAMENER_API_KEY_FILE` (override path to the API key file)
- `RAMENER_BASE_URL` (default `https://dashscope.aliyuncs.com/compatible-mode/v1`)
- `RAMENER_MODEL` (default `qwen-flash`)
- `RAMENER_PAGE_LIMIT` (default `3`)
- `RAMENER_TIMEOUT` (default `30.0` seconds)
- `RAMENER_MAX_TEXT_CHARS` (default `12000`)
- `RAMENER_LOG_PATH` (log file path)

## CLI Usage

After installation you can run either the module or the console script:

```bash
ramener path/to/report.pdf
# or
python -m ramener path/to/report.pdf
```

Helpful flags:

- `--dry-run` outputs the target filename without copying or trashing.
- `--page-limit 5` overrides the default pages parsed.
- `--log-file ~/Library/Logs/Ramener/ramener.log` stores verbose logs.

On completion the script copies the PDF to a new filename in the same directory and moves the original to the Trash.

## Finder Quick Action

1. Open **Automator** and create a new **Quick Action**.
2. Configure:
   - **Workflow receives current** → `PDF files`
   - **in** → `Finder`
   - Tick **Output replaces selected items** off.
3. Add the **Run Shell Script** action:
   - Shell: `/bin/zsh`
   - Pass input: `as arguments`
4. Script body example (adjust paths if the repo lives elsewhere):

```bash
source "$HOME/Works/ramener/.venv/bin/activate"
ramener "${1}"
```

If the workflow cannot export environment variables, save the API key to `~/.config/ramener/api_key` and the script will read it automatically.

5. Save as `Rename PDF via AI`. It appears in Finder’s right-click **Quick Actions** menu.

## Logging & Troubleshooting

- Verbose output streams to Automator, making macOS display any errors in a dialog.
- Use `--dry-run` to inspect metadata extraction without touching files.
- When the model response lacks enough detail, the filename falls back to the current date and original stem.

## Next Steps

Future improvements can include batch processing, configurable filename templates, OCR integration for scanned PDFs, and a SwiftUI front-end that wraps this CLI.
