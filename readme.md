# Installation

1. Download and install [Python 3.12.10](https://www.python.org/downloads/release/python-31210/)
   or a higher version of Python 3.12.
2. Open terminal in the root directory of this repository.
3. Initialize virtual environment in directory `.venv` and activate it according to the
   [tutorial](https://docs.python.org/3/library/venv.html).
4. Install and update necessary packages:
   1. Run `python -m pip install -U pip setuptools wheel` to update building packages.
   2. Run `python -m pip install playwright~=1.52.0` to install
      [playwright](https://github.com/microsoft/playwright).
   3. Run `playwright install chromium` to install Chromium browser for playwright.
5. Create empty file `questions.json` and fill it with `{}`.
6. Copy `config-template.toml` as `config.toml` and fill it.

# Usage

Check global variables in `scanner.py` and run the file via `python scanner.py`.
