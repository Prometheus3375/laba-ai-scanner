import json
import re
from collections import Counter
from collections.abc import Iterator, Set

import unicodedata

from .globals import QuestionLists, QuestionsJSON


def iterate_questions(
        filepath: str,
        /,
        categories: Set = frozenset(),
        subcategories: Set = frozenset(),
        topics: Set = frozenset(),
        ) -> Iterator[tuple[str, str, str, QuestionLists]]:
    """
    Reads JSON file with questions and iterates over their lists.

    Possible filtering can be added by specifying categories, subcategories and topics.
    If a filter set is empty, then no filtering is made for that set.
    """
    with open(filepath) as f:
        questions: QuestionsJSON = json.load(f)

    for category, category_dict in questions.items():
        if categories and category not in categories: continue

        for subcategory, topic_dict in category_dict.items():
            if subcategories and subcategory not in subcategories: continue

            for topic, q_lists in topic_dict.items():
                if topics and topic not in topics: continue

                yield category, subcategory, topic, q_lists


PATTERN_SYMBOLS = re.compile(r'[^\s\w]')


def count_words(questions: Iterator[str], output_filepath: str, /) -> None:
    """
    Counts words in the given questions and saves the result in the given output file.
    """
    counter = Counter()
    for question in questions:
        question = question.lower()
        question = PATTERN_SYMBOLS.sub(' ', question)
        counter.update(question.split())

    max_count_length = len(str(max(counter.values())))
    max_word_length = max(map(len, counter))
    with open(output_filepath, 'w') as f:
        for word, count in counter.most_common():
            f.write(f'{word:{max_word_length}}: {count:{max_count_length}}\n')


def strip_accents(text: str, /) -> str:
    """
    Removes accents in the given text.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
        )


__all__ = 'iterate_questions', 'count_words', 'strip_accents'
