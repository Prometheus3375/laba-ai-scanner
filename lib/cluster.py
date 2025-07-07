import sys
from collections.abc import Iterable, Iterator, Sequence
from operator import itemgetter
from typing import Any, Self, overload

from sentence_transformers import SentenceTransformer
from sklearn.cluster import HDBSCAN

from .globals import PreprocessFunc

_FIRST_ITEM = itemgetter(0)
_SECOND_ITEM = itemgetter(1)


@Sequence.register
class Cluster:
    """
    A class repressing a cluster of strings.
    """
    __slots__ = '_data', '_probabilities', '_core_idx'

    def __init__(
            self,
            data: Iterable[str],
            probabilities: Iterable[float],
            core_sample: str,
            /,
            ) -> None:
        data_prob = sorted(zip(data, probabilities, strict=True), key=_FIRST_ITEM)
        self._data = tuple(map(_FIRST_ITEM, data_prob))
        self._probabilities = tuple(map(_SECOND_ITEM, data_prob))
        self._core_idx = self._data.index(core_sample)

    @property
    def core_sample(self, /) -> str:
        """
        Core sample of this cluster.
        """
        return self._data[self._core_idx]

    @classmethod
    def from_group(cls, group: dict[str, float], medoid: str, /) -> Self:
        """
        Creates an instance of this class from a group of string with the given medoid.
        """
        return cls(group, group.values(), medoid)

    @classmethod
    def from_single(cls, sample: str, /) -> Self:
        """
        Creates an instance of this class from a single sample.
        """
        return cls([sample], [1], sample)

    def describe(self, /) -> str:
        """
        Verbosely lists all samples from this cluster with their probabilities.
        The core sample will be marked with '>'.
        """
        max_length = max(map(len, self._data))
        result = []
        for i, (q, p) in enumerate(zip(self._data, self._probabilities)):
            if i == self._core_idx:
                result.append(f'> {q:{max_length}}: {p:.6f}')
            else:
                result.append(f'- {q:{max_length}}: {p:.6f}')

        return '\n'.join(result)

    def __repr__(self, /) -> str:
        return (
            f'{self.__class__.__name__}('
            f'{self._data}, '
            f'{self._probabilities}, '
            f'{self.core_sample!r}'
            f')'
        )

    def __iter__(self, /) -> Iterator[str]:
        return iter(self._data)

    def __contains__(self, item: Any, /) -> bool:
        return item in self._data

    def __len__(self, /) -> int:
        return len(self._data)

    def __reversed__(self, /) -> Iterator[str]:
        return reversed(self._data)

    @overload
    def __getitem__(self, index: int, /) -> str: ...
    @overload
    def __getitem__(self, slice_: slice, /) -> Sequence[str]: ...

    def __getitem__(self, item, /):
        return self._data[item]

    def index(self, value: str, /, start: int = 0, stop: int = sys.maxsize) -> int:
        """
        Returns the first index where the given value occurs.
        If the value is not present, raises :class:`ValueError`.

        The optional arguments ``start`` and ``end`` are interpreted as in the slice notation
        and are used to limit the search to a particular subsequence of the cluster.
        The returned index is computed relative to the beginning of the full cluster
        rather than the ``start`` argument.
        """
        indices = range(*slice(start, stop).indices(len(self._data)))
        for idx in indices:
            sample = self._data[idx]
            if value is sample or value == sample:
                return idx

        raise ValueError(f'{value!r} is not in the cluster')

    def count(self, value: str, /) -> int:
        """
        Returns the number of occurrences inside this cluster of the given value.
        """
        return sum(1 for v in self._data if v is value or v == value)


def clusterize_sentences(
        data: Sequence[str],
        preprocess_func: PreprocessFunc,
        model: SentenceTransformer,
        hdbscan_params: dict[str, Any],
        /,
        ) -> list[Cluster]:
    """
    Preprocesses the given data with the given preprocessing function,
    then evaluates embeddings using :class:`SentenceTransformer` with the given model
    and then applies HDBSCAN with the given parameters to get clusters.

    Returns the list of resulting clusters.
    """
    prep_data = list(preprocess_func(data))
    embeddings = model.encode(prep_data, convert_to_numpy=True)

    hdbscan_params['store_centers'] = 'medoid'
    est = HDBSCAN(**hdbscan_params)
    est.fit(embeddings)

    max_label = max(est.labels_)
    groups = [{} for _ in range(max_label + 1)]
    clusters = []

    for sentence, label, prob in zip(data, est.labels_, est.probabilities_, strict=True):
        if label == -1:
            clusters.append(Cluster.from_single(sentence))
        else:
            groups[label][sentence] = prob

    embed2sent = dict(zip(map(tuple, embeddings), data))
    for group, medoid_embed in zip(groups, est.medoids_, strict=True):
        medoid_embed = tuple(medoid_embed)
        clusters.append(Cluster.from_group(group, embed2sent[medoid_embed]))

    return clusters


__all__ = 'Cluster', 'clusterize_sentences',
