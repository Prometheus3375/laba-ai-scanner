import csv
import re
from collections.abc import Iterator, Sequence
from logging import getLogger
from typing import Protocol

from .cluster import clusterize_sentences
from .configs import AnalyzerConfig
from .functions import iterate_questions
from .globals import PreprocessFunc

logger = getLogger('analyzer')


def make_preprocessing_function(config: AnalyzerConfig, /) -> PreprocessFunc:
    """
    Creates a preprocessing function from the given config.
    """
    text_to_replace = config.text_to_replace.copy()
    pattern_text_to_remove = re.compile('|'.join(config.text_to_remove), re.I)

    def preprocess(data: Sequence[str], /) -> Iterator[str]:
        for s in data:
            # Replace text
            for old, new in text_to_replace.items():
                s = s.replace(old, new)

            # Remove text
            s = pattern_text_to_remove.sub(' ', s)
            # Clear punctuation on edges
            s = s.strip(' .,;:')
            # Purge consecutive spaces
            s = ' '.join(s.split())
            yield s

    return preprocess


class RowMaker(Protocol):
    """
    Protocol describing functions which makes row.
    """
    def __call__(
            self,
            category: str,
            subcategory: str,
            topic: str,
            level: int,
            question: str,
            flag: bool,
            /,
            ) -> list: ...


def make_row_maker(config: AnalyzerConfig, /) -> RowMaker:
    """
    Creates a :class:`RowMaker` from the given config.
    """
    def make_row(
            category: str,
            subcategory: str,
            topic: str,
            level: int,
            question: str,
            flag: bool,
            /,
            ) -> list:
        row = []
        if config.include_category: row.append(category)
        if config.include_subcategory: row.append(subcategory)
        if config.include_topic: row.append(topic)

        row.append(level)
        row.append(question)
        if config.include_duplicates:
            row.append(flag)

        return row

    return make_row


def analyze(config: AnalyzerConfig, /) -> None:
    """
    Runs analysis using the given configuration.
    """
    logger.info('Starting the analyzer...')

    model_name = config.sentence_transformer_model
    hdbscan_params = config.hdbscan_params.copy()
    preprocess = make_preprocessing_function(config)
    make_row = make_row_maker(config)

    iterator = iterate_questions(
        config.input_filepath,
        config.categories,
        config.subcategories,
        config.topics,
        )

    csvfile = None
    count_total = 0
    count_unique = 0
    count_written = 0
    try:
        csvfile = open(config.output_filepath, 'w', newline='')
        writer = csv.writer(csvfile, dialect='excel')

        logger.info('The analyzer is started')
        for category, subcategory, topic, q_lists in iterator:
            logger.info(f'Analyzing questions from topic {topic!r}')
            for level, q_list in enumerate(q_lists.values(), 2):
                clusters = clusterize_sentences(
                    q_list,
                    preprocess,
                    model_name,
                    hdbscan_params,
                    )

                for cluster in clusters:
                    count_total += len(cluster)
                    count_unique += 1
                    if config.include_duplicates:
                        for question in sorted(cluster):
                            flag = question is not cluster.core_sample
                            row = make_row(category, subcategory, topic, level, question, flag)
                            writer.writerow(row)
                            count_written += 1

                    else:
                        question = cluster.core_sample
                        row = make_row(category, subcategory, topic, level, question, False)
                        writer.writerow(row)
                        count_written += 1

    except KeyboardInterrupt:
        pass

    except Exception:
        logger.exception('An error has occurred')

    finally:
        if csvfile:
            logger.info(f'Saving result to {config.output_filepath!r}')
            csvfile.close()

        logger.info(
            f'The analyzer is stopped. '
            f'Counts: '
            f'total = {count_total}, '
            f'unique = {count_unique}, '
            f'written = {count_written}'
            )


__all__ = 'analyze',
