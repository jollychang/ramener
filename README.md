# Ramener - AI PDF Renamer

Ramener reads the first few pages of a PDF, calls Aliyun Bailian (`qwen3-omni-flash`) to extract metadata, then renames the file to `YYYY-MM-DD_Source_Title.pdf`. It is optimised for macOS and ships as a standalone app plus light Finder integrations.

## macOS Install & First Run

1. Build (or download) the latest `Ramener.dmg` and drag `Ramener.app` into `/Applications`.
2. Launch `Ramener.app`. If no credentials are found, a native settings window appears—fill in the service name, API key, model, and base URL. Values are saved to `~/.config/ramener/settings.json` for both the app and CLI.
   - **API key placement**:
     - Preferred: in the settings window, paste the Aliyun Bailian key (format typically `sk-...`).
     - CLI-friendly: store the key in `~/.config/ramener/api_key` (first line only) or export `RAMENER_API_KEY`.
   - Model/base URL default to Aliyun’s public endpoint; customise only if you use a private gateway.
3. Open Finder and select any PDF, then choose your preferred integration:
   - Double-click `Ramener.app` and browse to a PDF when prompted, or
   - Add the toolbar/script integrations below for one-click access.

## Finder Toolbar Button (Optional)

Run the helper script to generate a ready-to-use toolbar applet:

```bash
./scripts/install_finder_toolbar.sh
```

The script creates `~/Applications/Ramener Toolbar.app`, detects an installed `ramener` CLI or the bundled `/Applications/Ramener.app`, and then opens Finder so you can drag the helper into the toolbar (`View → Customize Toolbar…`). Clicking the button processes the selected PDFs and reveals the renamed file.

## Finder Quick Action (Optional)

1. Open **Automator** → **Quick Action**.
2. Configure the workflow to receive `PDF files` in `Finder` and ensure **Output replaces selected items** is unchecked.
3. Add a **Run Shell Script** action with:
   - Shell: `/bin/zsh`
   - Pass input: `as arguments`
4. Example script body:

   ```bash
   "/Applications/Ramener.app/Contents/MacOS/ramener" "${1}"
   ```

   (Adjust if you keep the app elsewhere.)
5. Save as `Rename PDF via AI`. It now appears under Finder → **Quick Actions**.

## Command-Line Usage (Advanced)

The app bundle includes a console entry point. After `pip install -e '.[mac]'` (for contributors) or when the CLI is otherwise available, you can run:

```bash
ramener /path/to/report.pdf
```

Helpful flags:
- `--dry-run` prints the target filename without copying or trashing.
- `--page-limit`, `--max-text-chars`, and `--ocr-model` tune extraction behaviour.
- `--settings` opens the macOS settings window from the terminal.

## Logging & Troubleshooting

- Detailed logs roll to `~/Library/Logs/Ramener/ramener.log` by default; override with `--log-file` or `RAMENER_LOG_PATH`.
- To debug a frozen app run, execute `/Applications/Ramener.app/Contents/MacOS/ramener --verbose --log-file ~/Desktop/ramener-debug.log`.
- OCR fallback needs Poppler (`brew install poppler`) plus Pillow/pdf2image when running from source.
- Failures surface as macOS alerts when triggered via Automator/toolbar.

## Developer Setup

Ramener is packaged with PyInstaller, but the following is useful for local development:

- Requirements: macOS, Python 3.10+, Poppler (for OCR), Aliyun Bailian API access.
- Bootstrap environment:

  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -e '.[mac]'
  ```

- Optional environment overrides:
  `RAMENER_API_KEY_FILE`, `RAMENER_BASE_URL`, `RAMENER_MODEL`, `RAMENER_OCR_MODEL`, `RAMENER_PAGE_LIMIT`, `RAMENER_TIMEOUT`, `RAMENER_MAX_TEXT_CHARS`, `RAMENER_LOG_PATH`, `RAMENER_SERVICE_NAME`.

## Building the macOS Bundle

1. Ensure PyInstaller is installed in your environment (`pip install pyinstaller`).
2. Run `./scripts/build_dmg.sh`.
3. The script produces `dist/Ramener.app` and `dist/Ramener.dmg`. Codesign and notarise `dist/Ramener.app` as needed before distributing the DMG.

Icons live under `packaging/` (`ramener.png` source, `ramener.icns` bundle icon). If you edit the PNG, regenerate the `.icns` with `python scripts/make_icns.py` before rebuilding.

## Publishing to GitHub Releases

1. Build artefacts locally:
   ```bash
   ./scripts/build_dmg.sh
   ```
   This produces `dist/Ramener.app` and `dist/Ramener.dmg`.
2. Tag the release:
   ```bash
   git tag v0.2.0
   git push origin main --tags
   ```
3. Create a GitHub release (web UI or `gh release create v0.2.0 dist/Ramener.dmg --notes "…"`) and attach `dist/Ramener.dmg`. Optionally add `dist/Ramener.app` for users who prefer copying bundles manually.
4. Include release notes summarising changes, system requirements, and any notarisation status.

You can automate the process via the helper script:

```bash
./scripts/create_release.sh v0.2.0 --notes "Bug fixes and Finder integration improvements"
```

The script rebuilds the DMG, creates the Git tag if it doesn’t already exist, pushes it to the `origin` remote (override with `GIT_REMOTE=upstream`), and then creates or updates the GitHub release (requires the GitHub CLI `gh`).
