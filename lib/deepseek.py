import json
import re
from http.client import HTTPResponse
from json import JSONDecodeError
from logging import getLogger
from typing import Any, Self
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from .configs import DeepSeekConfig

logger = getLogger('deepseek')

PATTERN_BARS_AND_SPACES = re.compile(r'\s*\n(\|\n+)+\s*|\s+')
PATTERN_TRAILING_SPACES = re.compile(r'[^\S\n]+\n')


def _replace_bars_and_spaces(m: re.Match, /) -> str:
    if m[0].isspace(): return ' '

    return '\n' * m[0].count('|')


def format_system_prompt(prompt: str, /) -> str:
    """
    Properly formats a system prompt for LLMs.
    """
    return PATTERN_BARS_AND_SPACES.sub(_replace_bars_and_spaces, prompt.strip())


def format_user_message(message: str, /) -> str:
    """
    Properly formats a user message for LLMs.
    """
    return message.strip()


def format_response(response: str, /) -> str:
    """
    Properly formats a response from LLMs.
    """
    return PATTERN_TRAILING_SPACES.sub('\n', response).rstrip()


class DeepSeekClient:
    """
    A client for querying DeepSeek LLM.
    """
    __slots__ = '_api_key', '_system_prompt', '_api_params'

    url = 'https://api.deepseek.com/chat/completions'

    def __init__(self, /, api_key: str, system_prompt: str, **api_params: Any) -> None:
        self._api_key = api_key
        self._system_prompt = format_system_prompt(system_prompt)
        self._api_params = api_params

    @classmethod
    def from_config(cls, config: DeepSeekConfig, /) -> Self:
        """
        Creates an instance using data from the given configuration.
        """
        with open(config.system_prompt_filepath) as f:
            system_prompt = f.read()

        return cls(
            api_key=config.api_key,
            system_prompt=system_prompt,
            **config.api_params,
            )

    def get_response_for_user_message(self, message: str, /) -> str:
        """
        Calls API with the given message and returns the response.

        If the message is the empty string or consists purely from space-like symbols,
        immediately returns the empty string performing no API calls.

        If the API call fails, logs the error occurred
        and returns the empty string without generating a report.
        """
        if not message or message.isspace():
            return ''

        message = format_user_message(message)
        try:
            response = self._blocking_api_call(message)
        except HTTPError as exc:
            self._handle_api_call_error(exc)
            return ''

        return format_response(response)

    def _blocking_api_call(self, message: str, /) -> str:
        req = self._prepare_request(message, False)

        response: HTTPResponse
        with urlopen(req) as response:
            data = json.loads(response.read())

        return data['choices'][0]['message']['content']

    def _prepare_request(self, message: str, is_stream: bool, /) -> Request:
        data = self._api_params.copy()
        data['model'] = self._api_params.get('model')
        data['stream'] = is_stream
        data['messages'] = [
            {'role': 'system', 'content': self._system_prompt},
            {'role': 'user', 'content': message},
            ]

        body = json.dumps(data, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        headers = {
            'Content-Type':  'application/json',
            'Accept':        'application/json',
            'Authorization': f'Bearer {self._api_key}'
            }

        return Request(self.url, body, headers, method='POST')

    @staticmethod
    def _handle_api_call_error(exc: HTTPError, /) -> None:
        exc_msg = exc.read()
        try:
            data = json.loads(exc_msg)
        except JSONDecodeError:
            error_str = ' ' + exc_msg.decode()
        else:
            error_str = '\n' + json.dumps(data['error'], ensure_ascii=False, indent=2)

        logger.error(f'An error occurred when requesting DeepSeek:{error_str}')


__all__ = 'DeepSeekClient',
