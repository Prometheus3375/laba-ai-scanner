import sys
from collections.abc import Iterator, Sequence
from typing import Any, NamedTuple, Self, overload

from numpy import array_equal, ndarray
from sentence_transformers import SentenceTransformer
from sklearn.cluster import HDBSCAN

from .globals import PreprocessFunc


class Sample(NamedTuple):
    """
    A class representing a single sample.
    """
    sentence: str
    embedding: ndarray[float]
    probability: float


_ATTR_SENTENCE = Sample.sentence.__get__
_ATTR_EMBEDDING = Sample.embedding.__get__
_ATTR_PROBABILITY = Sample.probability.__get__


@Sequence.register
class Cluster:
    """
    A class repressing a cluster of strings.
    """
    __slots__ = '_strings', '_embeddings', '_probabilities'

    _core_idx = 0

    def __init__(self, samples: Sequence[Sample], core_sample: Sample, /) -> None:
        # Use sorted to sort and copy the sequence.
        samples = sorted(samples, key=_ATTR_SENTENCE)
        for i, sample in enumerate(samples):
            if sample == core_sample:
                if i != self._core_idx:
                    del samples[i]
                    samples.insert(self._core_idx, sample)

                break
        else:
            raise ValueError(f'core sample {core_sample!r} is not in the given samples')

        self._strings: tuple[str, ...] = tuple(map(_ATTR_SENTENCE, samples))
        self._embeddings: tuple[ndarray[float], ...] = tuple(map(_ATTR_EMBEDDING, samples))
        self._probabilities: tuple[float, ...] = tuple(map(_ATTR_PROBABILITY, samples))

    @classmethod
    def from_single(cls, sentence: str, embedding: ndarray[float], /) -> Self:
        """
        Creates an instance of this class from a single sample.
        """
        sample = Sample(sentence, embedding, 1)
        return cls([sample], sample)

    @property
    def core_string(self, /) -> str:
        """
        Core string of this cluster.
        """
        return self._strings[self._core_idx]

    @property
    def strings(self, /) -> Sequence[str]:
        """
        Strings forming this cluster.
        """
        return self._strings

    @property
    def embeddings(self, /) -> Sequence[ndarray[float]]:
        """
        Embeddings of the strings forming this cluster.
        """
        return self._embeddings

    @property
    def probabilities(self, /) -> Sequence[float]:
        """
        Probabilities of the strings forming this cluster.
        """
        return self._probabilities

    @property
    def samples(self, /) -> list[Sample]:
        """
        Samples forming this cluster.
        """
        return [
            Sample(s, e, p)
            for s, e, p in zip(self._strings, self._embeddings, self._probabilities, strict=True)
            ]

    def describe(self, /) -> str:
        """
        Verbosely lists all samples from this cluster with their probabilities.
        The core sample will be marked with '>'.
        """
        max_length = max(map(len, self._strings))
        core_string = self.core_string
        result = []
        for s, p in zip(self._strings, self._probabilities):
            if s is core_string:
                result.append(f'> {s:{max_length}}: {p:.6f}')
            else:
                result.append(f'- {s:{max_length}}: {p:.6f}')

        return '\n'.join(result)

    def __repr__(self, /) -> str:
        samples = self.samples
        return (
            f'{self.__class__.__name__}('
            f'{samples}, '
            f'{samples[self._core_idx]!r}'
            f')'
        )

    # Consider only strings for Sequence operations.

    def __iter__(self, /) -> Iterator[str]:
        return iter(self._strings)

    def __contains__(self, item: Any, /) -> bool:
        return item in self._strings

    def __len__(self, /) -> int:
        return len(self._strings)

    def __reversed__(self, /) -> Iterator[str]:
        return reversed(self._strings)

    @overload
    def __getitem__(self, index: int, /) -> str: ...
    @overload
    def __getitem__(self, slice_: slice, /) -> Sequence[str]: ...

    def __getitem__(self, item, /):
        return self._strings[item]

    def index(self, value: str, /, start: int = 0, stop: int = sys.maxsize) -> int:
        """
        Returns the first index where the given value occurs.
        If the value is not present, raises :class:`ValueError`.

        The optional arguments ``start`` and ``end`` are interpreted as in the slice notation
        and are used to limit the search to a particular subsequence of the cluster.
        The returned index is computed relative to the beginning of the full cluster
        rather than the ``start`` argument.
        """
        indices = range(*slice(start, stop).indices(len(self._strings)))
        for idx in indices:
            sample = self._strings[idx]
            if value is sample or value == sample:
                return idx

        raise ValueError(f'{value!r} is not in the cluster')

    def count(self, value: str, /) -> int:
        """
        Returns the number of occurrences inside this cluster of the given value.
        """
        return sum(1 for v in self._strings if v is value or v == value)

    def __hash__(self, /) -> int:
        return self._strings.__hash__()

    def __eq__(self, other: Any, /) -> bool:
        if isinstance(other, Cluster):
            return self._strings == other._strings

        return NotImplemented

    def __lt__(self, other: Self, /) -> bool:
        if isinstance(other, Cluster):
            return self._strings < other._strings

        return NotImplemented


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

    label_range = range(max(est.labels_) + 1)
    groups: list[list[Sample]] = [[] for _ in label_range]
    medoids: list[Sample] = [... for _ in label_range]
    clusters = []

    it: Iterator[tuple[int, str, ndarray[float], float]]
    it = zip(est.labels_, data, embeddings, est.probabilities_, strict=True)
    for label, sentence, embedding, probability in it:
        if label <= -1:
            clusters.append(Cluster.from_single(sentence, embedding))
        else:
            sample = Sample(sentence, embedding, probability)
            groups[label].append(sample)
            if array_equal(embedding, est.medoids_[label]):
                medoids[label] = sample

    clusters.extend(
        Cluster(group, medoid)
        for group, medoid in zip(groups, medoids, strict=True)
        )

    # Sort clusters to preserve their order
    # if different settings yield the same result.
    clusters.sort()
    return clusters


__all__ = 'Cluster', 'clusterize_sentences',
