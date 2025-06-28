# Installation

1. Download and install [Python 3.12.10](https://www.python.org/downloads/release/python-31210/)
   or a higher version of Python 3.12.
2. Open terminal in the root directory of this repository.
3. Initialize virtual environment in directory `.venv` and activate it according to the
   [tutorial](https://docs.python.org/3/library/venv.html).
4. Install and update necessary packages:
   1. Run `python -m pip install -U pip setuptools wheel` to update building packages.
   2. Run `python -m pip install pip-tools~=7.4.0` to install
      [pip-tools](https://github.com/jazzband/pip-tools/).
   3. Install PyTorch according to the [guide](https://pytorch.org/get-started/locally).
   4. Run `python -m piptools compile -U --strip-extras` to generate file `requirements.txt`.
   5. Run `python -m pip install -r requirements.txt --no-deps` to install all necessary packages.
   6. Run `playwright install chromium` to install Chromium browser for playwright.
5. Create empty file `questions.json` and fill it with `{}`.
6. Copy `config-template.toml` as `config.toml` and fill it.

# Usage

## Retrieving questions from Laba.AI

Start scanning Laba.AI via running `python scanner.py` and follow log instructions.

Once script is completed, all recorded questions will be inside file
`questions.json` per category, subcategory, topic and question level.

## Exporting questions to CSV

Check global variables in `to_csv.py` and run the file via `python to_csv.py`.
Once script is completed, all questions from `questions.json` will be inside file `questions.csv`.
In addition, every row will have a boolean flag
whether its question duplicates another question of the same difficulty and topic.
