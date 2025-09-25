# Ramener - AI PDF Renamer

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

Skip finder “Quick Actions” if you prefer a Toolbar button? See **Automator Application** below.

## Logging & Troubleshooting

- Verbose output streams to Automator, making macOS display any errors in a dialog.
- Use `--dry-run` to inspect metadata extraction without touching files.
- When the model response lacks enough detail, the filename falls back to the current date and original stem.
- Basic PII scrubbing (emails, long numeric IDs) happens automatically before text is sent to the model to reduce moderation failures.

## Next Steps

Future improvements can include batch processing, configurable filename templates, OCR integration for scanned PDFs, and a SwiftUI front-end that wraps this CLI.

## Automator Application & Finder Toolbar Button

You can also create an Automator **Application** so the workflow can sit in Finder’s toolbar.

1. Launch Automator → New **Application**.
2. Add **Get Selected Finder Items** (ensures the current selection is forwarded).
3. Add **Run Shell Script** with the same shell (`/bin/zsh`) and script content as below:

```bash
source "$HOME/Works/ramener/.venv/bin/activate"

if [ "$#" -eq 0 ]; then
  osascript -e 'display alert "Ramener" message "Please select a PDF before running."' >/dev/null 2>&1
  exit 1
fi

new_files=()
for file in "$@"; do
  output=$(ramener "$file")
  exit_code=$?
  if [ "$exit_code" -eq 0 ] && [ -n "$output" ]; then
    new_files+=("$output")
  else
    printf 'Ramener failed for %s\n' "$file" >&2
  fi
done

if [ "${#new_files[@]}" -gt 0 ]; then
  last="${new_files[-1]}"
  sleep 0.2
  open -R "$last"
fi
```

4. Save to `~/Applications/Rename PDF via AI.app` (or another location).
5. In Finder, open `View → Customize Toolbar…`, then drag the new `.app` onto the toolbar. Clicking it now processes the selected PDFs and reveals the new file.
