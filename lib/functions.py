import json
import re
from collections import Counter

import unicodedata

from .globals import QuestionsJSON

PATTERN_SYMBOLS = re.compile(r'[^\s\w]')


def count_words(questions_filepath: str, output_filepath: str, /) -> None:
    """
    Counts words inside JSON file with questions and saves the result in the given output file.
    """
    with open(questions_filepath) as f:
        questions: QuestionsJSON = json.load(f)

    counter = Counter()
    for cat_dict in questions.values():
        for sub_dict in cat_dict.values():
            for q_lists in sub_dict.values():
                for q_list in q_lists.values():
                    for question in q_list:
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


__all__ = 'count_words', 'strip_accents'
