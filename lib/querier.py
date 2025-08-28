import csv
from logging import getLogger
from typing import Any

from lib.configs import QuerierConfig
from lib.deepseek import DeepSeekClient

logger = getLogger('querier')


def get_predefined_answers(filepath: str, /) -> dict[tuple[Any, ...], str]:
    """
    Opens a CSV file and creates a mapping between all but last columns and the last column.
    """
    if not filepath: return {}

    result = {}
    with open(filepath, newline='') as f:
        reader = csv.reader(f, dialect='excel')
        for row in reader:
            answer = row.pop()
            if answer and not answer.isspace():
                _ = row.pop()  # pop flag
                result[*row] = answer

    return result


def query(config: QuerierConfig, /) -> None:
    """
    Runs querier using the given configuration.
    """
    logger.info('Starting the querier...')

    client = DeepSeekClient.from_config(config.deepseek)
    predefined = get_predefined_answers(config.predefined_filepath)
    logger.info(f'Loaded {len(predefined)} answers')

    frequency = config.log_frequency
    inp = None
    out = None
    line_no = 0
    count_predefined = 0
    count_queried = 0
    count_queried_err = 0
    count_ignored = 0
    try:
        inp = open(config.input_filepath, newline='')
        reader = csv.reader(inp, dialect='excel')
        out = open(config.output_filepath, 'w', newline='')
        writer = csv.writer(out, dialect='excel')

        logger.info('The querier is started')
        for line_no, row in enumerate(reader, 1):
            col_tuple = tuple(row[:-1])
            answer = predefined.get(col_tuple)
            if answer:
                count_predefined += 1
            else:
                flag = row[-1].lower()
                is_original = flag == 'false'
                question = row[-2]
                if is_original:
                    answer = client.get_response_for_user_message(question)
                    if answer:
                        count_queried += 1
                    else:
                        logger.warning(f'Empty answer for question at line {line_no}')
                        count_queried_err += 1
                else:
                    answer = ''
                    count_ignored += 1

            row.append(answer)
            writer.writerow(row)

            if line_no % frequency == 0:
                logger.info(
                    f'Answer counts: '
                    f'predefined = {count_predefined}, '
                    f'queried = {count_queried}'
                    )

    finally:
        if inp: inp.close()

        if out:
            logger.info(f'Saving result to {config.output_filepath!r}')
            out.close()

        logger.info('The querier is stopped')

        logger.info(
            f'Question counts: '
            f'total = {line_no}, '
            f'ignored = {count_ignored}, '
            f'failed to query = {count_queried_err}'
            )

        logger.info(
            f'Answer counts: '
            f'predefined = {count_predefined}, '
            f'queried = {count_queried}'
            )
