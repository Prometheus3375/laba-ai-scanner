from typing import TypedDict


class QuestionSets(TypedDict):
    q1: set[str]
    q2: set[str]
    q3: set[str]


type Questions = dict[str, dict[str, dict[str, QuestionSets]]]

__all__ = 'QuestionSets', 'Questions'
