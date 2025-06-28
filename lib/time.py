from collections.abc import Callable, Iterator
from contextlib import contextmanager

from time import perf_counter

DURATION_UNIT_NAMES = 'yr', 'mo', 'wk', 'd', 'h', 'm', 's'
DURATION_UNITS = {
    'years':        60 * 60 * 24 * 365,
    'months':       60 * 60 * 24 * 30,
    'weeks':        60 * 60 * 24 * 7,
    'days':         60 * 60 * 24,
    'hours':        60 * 60,
    'minutes':      60,
    'seconds':      1,
    }


def _generate_non_zero_units[T](values: list[T], /) -> Iterator[tuple[T, str]]:
    it = zip(values, DURATION_UNIT_NAMES)
    for value_unit in it:
        if value_unit[0] != 0:
            yield value_unit
            yield from it
            break
    else:
        # The iterator is exhausted, yield the very last value with its unit
        yield values[-1], DURATION_UNIT_NAMES[-1]


def format_seconds(seconds: float, /) -> str:
    """
    Formats the given number of seconds into
    years, months, weeks, days, hours, minutes and seconds.
    """
    data = []
    for mul in DURATION_UNITS.values():
        value, seconds = divmod(seconds, mul)
        data.append(int(value))

    return ' '.join(
        f'{value}{unit}'
        for value, unit in _generate_non_zero_units(data)
        )


@contextmanager
def time_tracker(
        msg_fmt: str = 'Time elapsed: {}',
        /,
        log: Callable[[str], None] = print,
        ) -> Iterator[None]:
    """
    A context manager to track time of the underlined block of code.
    Whether the block fails or succeeds, the time is logged.

    :param msg_fmt: The format of the logged string,
      must contain one positional format parameter for the time entry.
    :param log: The callable for logging the message with time in the given format.
    """
    start_time = perf_counter()
    try:
        yield
    finally:
        log(msg_fmt.format(format_seconds(perf_counter() - start_time)))


__all__ = 'DURATION_UNIT_NAMES', 'DURATION_UNITS', 'format_seconds', 'time_tracker'
