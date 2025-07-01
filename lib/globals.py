from collections.abc import Callable, Iterator, Sequence
from typing import TypedDict


class QuestionSets(TypedDict):
    q1: set[str]
    q2: set[str]
    q3: set[str]


class QuestionLists(TypedDict):
    q1: list[str]
    q2: list[str]
    q3: list[str]


type Questions = dict[str, dict[str, dict[str, QuestionSets]]]
type QuestionsJSON = dict[str, dict[str, dict[str, QuestionLists]]]
type PreprocessFunc = Callable[[Sequence[str]], Iterator[str]]

__all__ = 'QuestionSets', 'QuestionLists', 'Questions', 'QuestionsJSON', 'PreprocessFunc'
