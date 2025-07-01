def main() -> None:
    from argparse import ArgumentParser

    parser = ArgumentParser(
        description='A script for analyzing questions gathered from Laba.AI',
        add_help=False,
        )

    parser.add_argument(
        'config_file',
        nargs='?',
        default='config.toml',
        help='Path to the configuration file. Defaults to "config.toml".',
        )

    parser.add_argument(
        '-h',
        '--help',
        action='help',
        help='If specified, the script shows this help message and exits.',
        )

    args = parser.parse_args()

    from logging import getLogger
    from lib.configs import read_config
    from lib.time import time_tracker

    config = read_config(args.config_file).analyzer
    logger = getLogger('script')

    with time_tracker('The script is stopped. Time elapsed: {}', logger.info):
        logger.info('Press Ctrl+C to stop this script')

        from lib.analyzer import analyze

        analyze(config)


if __name__ == '__main__':
    main()
