import tomllib
from logging.config import dictConfig
from typing import Any

from pydantic import BaseModel, Field, PositiveInt


class BaseConfig(BaseModel, strict=True, extra='forbid', frozen=True):
    """
    Base class for all configs with necessary model configuration flags.
    """


class ScannerConfig(BaseConfig):
    """
    Configuration for a scanner.
    """
    url: str
    full_name: str
    email: str
    coordinator_email: str
    output_filepath: str
    categories: frozenset[str] = Field(strict=False)
    subcategories: frozenset[str] = Field(strict=False)
    topics: frozenset[str] = Field(strict=False)
    times_per_topic: PositiveInt


class WholeConfig(BaseConfig, extra='ignore'):
    """
    A collection of all possible configurations.
    """
    scanner: ScannerConfig
    logging: dict[str, Any]


def read_config(filepath: str, /) -> WholeConfig:
    """
    Reads configuration file, initializes logging
    and returns an instance of :class:`WholeConfig`.
    """
    with open(filepath, 'rb') as f:
        config = WholeConfig.model_validate(tomllib.load(f))

    dictConfig(config.logging)
    return config


__all__ = 'BaseConfig', 'ScannerConfig', 'WholeConfig', 'read_config'
