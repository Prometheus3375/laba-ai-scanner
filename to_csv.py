import csv
import json
from collections.abc import Iterator

import unicodedata
from sentence_transformers import SentenceTransformer

from lib.globals import QuestionsJSON
from lib.time import time_tracker

INPUT_FILE = 'questions.json'
"""
Input JSON file.
"""

OUTPUT_FILE = 'questions.csv'
"""
Output CSV file.
"""

CATEGORY = 'Методы инженерии и анализа данных'
"""
Category to write into CSV file.
"""

SIMILARITY_THRESHOLD = 0.83
"""
A number between 0 and 1.
If similarity score for two questions is higher than this number,
they are considered similar.
Set to 1 or 0 to disable scoring.
"""

MODEL = SentenceTransformer('all-MiniLM-L6-v2')
"""
Model to use for finding similar questions.
"""


def strip_accents(text: str) -> str:
    """
    Removes accents in the given text.
    """
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
        )


def analyze_questions(data: list[str], threshold: float, /) -> Iterator[tuple[str, bool]]:
    """
    Analyzes the given list of questions and finds similar ones.
    Returns an iterator over tuples of two elements.
    The first element is a question, and the second element is a boolean flag
    whether this question is similar to any previous one.

    Two questions are considered similar
    if their similarity score is greater than or equal to the given threshold.
    If the threshold is not in open range (0, 1), then no analysis is made.
    """
    length = len(data)
    flags = [False] * length

    if 0 < threshold < 1:
        embeddings = MODEL.encode(list(map(strip_accents, data)))
        similarities = MODEL.similarity(embeddings, embeddings)

        # For every sentence...
        for i in range(length):
            # ... check similarity with every next sentence.
            # No need to check similarity with previous ones
            # as it was checked in previous iterations.
            for ii in range(i + 1, length):
                sim = similarities[i, ii]
                # If similarity is >= than a threshold,
                # then mark other sentence as a duplicate.
                # DO NOTHING if similarity is less!
                if sim >= threshold:
                    flags[ii] = True

    return zip(data, flags)


def main() -> None:
    with open(INPUT_FILE) as f:
        data: QuestionsJSON = json.load(f)
        to_write = data[CATEGORY]

    with open(OUTPUT_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')
        for category, cat_dict in to_write.items():
            for topic, topic_dict in cat_dict.items():
                for question, flag in analyze_questions(topic_dict['q1'], SIMILARITY_THRESHOLD):
                    writer.writerow([category, topic, 2, question, flag])

                for question, flag in analyze_questions(topic_dict['q2'], SIMILARITY_THRESHOLD):
                    writer.writerow([category, topic, 3, question, flag])

                for question, flag in analyze_questions(topic_dict['q3'], SIMILARITY_THRESHOLD):
                    writer.writerow([category, topic, 4, question, flag])


if __name__ == '__main__':
    with time_tracker():
        main()
