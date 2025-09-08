import csv
import os
import re
from collections.abc import Iterator, Mapping, Sequence
from logging import getLogger
from typing import Protocol

from sentence_transformers import SentenceTransformer

from .cluster import clusterize_sentences
from .configs import AnalyzerConfig
from .functions import iterate_questions
from .globals import PreprocessFunc

logger = getLogger('analyzer')


def make_preprocessing_function(
        punctuation: str,
        text_to_replace: Mapping[str, str],
        text_to_remove: Sequence[str],
        /,
        ) -> PreprocessFunc:
    """
    Creates a preprocessing function from the given config.
    """
    pattern_text_to_remove = re.compile('|'.join(text_to_remove), re.I)
    pattern_spaces = re.compile(r'\s+')
    pattern_space_punctuation = re.compile(rf' ([{punctuation}])')
    space_punctuation = ' ' + punctuation

    def preprocess(data: Sequence[str], /) -> Iterator[str]:
        for s in data:
            # Replace text
            for old, new in text_to_replace.items():
                s = s.replace(old, new)

            # Remove text
            s = pattern_text_to_remove.sub(' ', s)
            # Remove punctuation on edges
            s = s.strip(space_punctuation)
            # Purge consecutive spaces
            s = pattern_spaces.sub(' ', s)
            # Remove spaces before punctuation
            s = pattern_space_punctuation.sub(r'\1', s)
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


def make_row_maker(
        *,
        include_category: bool,
        include_subcategory: bool,
        include_topic: bool,
        ) -> RowMaker:
    """
    Creates a :class:`RowMaker` with the given settings.
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
        if include_category: row.append(category)
        if include_subcategory: row.append(subcategory)
        if include_topic: row.append(topic)

        row.append(level)
        row.append(question)
        row.append(flag)

        return row

    return make_row


def analyze(config: AnalyzerConfig, /) -> None:
    """
    Runs analysis using the given configuration.
    """
    logger.info('Starting the analyzer...')

    model = SentenceTransformer(config.sentence_transformer_model)
    hdbscan_params = config.hdbscan_params.copy()
    preprocess = make_preprocessing_function(
        config.punctuation,
        config.text_to_replace.copy(),
        config.text_to_remove,
        )

    include_duplicates = config.include_duplicates
    make_row = make_row_maker(
        include_category=config.include_category,
        include_subcategory=config.include_subcategory,
        include_topic=config.include_topic,
        )

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
        csvfile_dir = os.path.dirname(config.output_filepath)
        if csvfile_dir:
            os.makedirs(csvfile_dir, exist_ok=True)

        csvfile = open(config.output_filepath, 'w', newline='')
        writer = csv.writer(csvfile, dialect='excel')

        logger.info('The analyzer is started')
        for category, subcategory, topic, q_lists in iterator:
            logger.info(f'Analyzing questions from topic {topic!r}')
            for level, q_list in enumerate(q_lists.values(), 2):
                clusters = clusterize_sentences(
                    q_list,
                    preprocess,
                    model,
                    hdbscan_params,
                    )

                for cluster in clusters:
                    count_total += len(cluster)
                    count_unique += 1
                    if include_duplicates:
                        for question in cluster:
                            flag = question is not cluster.core_string
                            row = make_row(category, subcategory, topic, level, question, flag)
                            writer.writerow(row)
                            count_written += 1

                    else:
                        question = cluster.core_string
                        row = make_row(category, subcategory, topic, level, question, False)
                        writer.writerow(row)
                        count_written += 1

    finally:
        if csvfile:
            logger.info(f'Saving result to {config.output_filepath!r}')
            csvfile.close()

        logger.info(
            f'The analyzer is stopped. '
            f'Question counts: '
            f'total = {count_total}, '
            f'unique = {count_unique}, '
            f'written = {count_written}'
            )


__all__ = 'analyze', 'make_preprocessing_function', 'make_row_maker'
