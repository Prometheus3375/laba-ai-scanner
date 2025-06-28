from argparse import ArgumentParser
from logging import getLogger

from lib.configs import read_config
from lib.scanner import Scanner
from lib.time import time_tracker


def main() -> None:
    parser = ArgumentParser(
        description='A script for scanning Laba.AI website for questions',
        add_help=False,
        )

    parser.add_argument(
        'config_file',
        nargs='?',
        default='config.toml',
        help='Path to the configuration file for the scanner. Defaults to "config.toml".',
        )

    parser.add_argument(
        '-h',
        '--help',
        action='help',
        help='If specified, the script shows this help message and exits.',
        )

    args = parser.parse_args()
    config = read_config(args.config_file)
    scanner = Scanner(config.scanner)
    logger = getLogger('script')

    with time_tracker('The script is stopped. Time elapsed: {}', logger.info):
        try:
            logger.info('Press Enter or Ctrl+C to stop this script')
            scanner.start()
            input()
            logger.info('Enter received, stopping the script...')
        except KeyboardInterrupt:
            logger.info('Ctrl+C received, stopping the script...')
        except Exception:
            logger.exception('An unknown error has occurred, the script will be stopped shortly')
        finally:
            scanner.stop()


if __name__ == '__main__':
    main()
