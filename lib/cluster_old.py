from collections.abc import Iterator, Sequence

from sentence_transformers import SentenceTransformer

from .globals import PreprocessFunc


def analyze_strings(
        data: Sequence[str],
        preprocess_func: PreprocessFunc,
        model_name: str,
        threshold: float,
        /
        ) -> Iterator[tuple[str, bool]]:
    """
    Preprocesses the given data with the given preprocessing function,
    evaluates embeddings using :class:`SentenceTransformer` with the given model,
    then analyzes them and finds similar ones.
    Returns an iterator over tuples of two elements.
    The first element is a string, and the second element is a boolean flag
    whether this string is similar to any previous one.

    Two strings are considered similar
    if their similarity score is greater than or equal to the given threshold.
    If the threshold is not in open range (0, 1), then no analysis is made.
    """
    length = len(data)
    flags = [False] * length

    if 0 < threshold < 1:
        model = SentenceTransformer(model_name)
        embeddings = model.encode(list(preprocess_func(data)))
        similarities = model.similarity(embeddings, embeddings)

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


__all__ = 'analyze_strings',
