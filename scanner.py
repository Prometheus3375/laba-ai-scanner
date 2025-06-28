import json
import tomllib
from collections import defaultdict
from datetime import datetime
from typing import Any

from playwright.sync_api import BrowserContext, Error, Page, expect, sync_playwright

from globals import *
from lib.time import time_tracker

CONFIG_FILE = 'config.toml'
"""
Path to a configuration file with login information.
"""

QUESTIONS_FILE = 'questions.json'
"""
Path to a file with questions.
"""

CATEGORIES = {'Методы инженерии и анализа данных'}
"""
Which categories to scan. Can be set to ``None`` to scan all of them.
"""

SUBCATEGORIES = {}
"""
Which subcategories to scan. Can be set to ``None`` to scam all of them.
"""

TOPICS = {}
"""
Which topics to scan. Can be set to ``None`` to scam all of them.
"""

TIMES_PER_TOPIC = 30
"""
How many times scan every topic.
"""

with open(CONFIG_FILE, 'rb') as _f:
    CONFIG = tomllib.load(_f)
    del _f


def open_laba_ai(context: BrowserContext, /) -> Page:
    """
    Opens Laba.AI platform and logs in.
    """
    page = context.new_page()
    page.goto(CONFIG['url'])
    page.get_by_placeholder('Name Surname', exact=True).fill(CONFIG['full_name'])
    emails = page.get_by_placeholder('Use corporate email address only', exact=True)
    emails.first.fill(CONFIG['email'])
    emails.last.fill(CONFIG['coordinator_email'])
    page.get_by_text('Verify', exact=True).click()
    return page


def get_topics(page: Page, /) -> dict[str, dict[str, list[str]]]:
    """
    Extracts topic hierarchy from the page.
    """
    topics = defaultdict(lambda: defaultdict(list))
    locator = page.get_by_role('checkbox')
    expect(locator.first).to_be_visible()

    for i in range(locator.count()):
        box = locator.nth(i)
        value = box.get_attribute('value')
        if value:
            major, minor, topic = value.split('___', maxsplit=2)
            topics[major][minor].append(topic)

    return topics


def read_existing_questions(filepath: str, topics: dict[str, dict[str, list[str]]], /) -> Questions:
    """
    Reads the give JSON with recorded questions, adds missing topics
    and converts question lists into sets.
    """
    with open(filepath) as f:
        questions: dict = json.load(f)

    for category, category_dict in topics.items():
        cat_dict = questions.setdefault(category, {})

        for subcategory, topic_names in category_dict.items():
            subcat_dict = cat_dict.setdefault(subcategory, {})

            for topic in topic_names:
                topic_dict = subcat_dict.setdefault(topic, {})
                for key in QuestionSets.__annotations__:
                    li = topic_dict.get(key)
                    if li is None:
                        topic_dict[key] = set()
                    else:
                        topic_dict[key] = set(li)

    return questions


def _convert_set(obj: Any, /) -> Any:
    if isinstance(obj, set):
        return sorted(obj)

    raise TypeError(f'Object of type {obj.__class__.__name__} is not JSON serializable')


def save_questions(questions: Questions, filepath: str, /) -> None:
    """
    Saves a dictionary with questions to a designated file in JSON format.
    """
    with open(filepath, 'w') as f:
        json.dump(questions, f, ensure_ascii=False, indent=2, default=_convert_set)
        f.write('\n')


def get_question_text(page: Page, /) -> str:
    """
    Gets text of a question in Laba.AI.
    """
    text = (
        page
        .locator('[class*="text-sm text-balance select-none pointer-events-none"]')
        .inner_text()
    )
    text = text.replace('ё', 'е').strip('.')
    text = ' '.join(text.split())
    return text


def record_questions(context: BrowserContext, topic_name: str, q_sets: QuestionSets, /) -> bool:
    """
    Opens Laba.AI, resets topic selection, selects the given topic and starts an exam.
    Then records questions encountered to the given ``q_sets``.
    Returns ``True`` on success and ``False`` otherwise.
    """
    with open_laba_ai(context) as page:
        # Remove default selection by clicking the first category.
        # .check() or .uncheck() do not work on the first checkbox as it is in a mixed state.
        # They also often throw an error for an unknown reason when used of the first category.
        first_category = page.get_by_role('checkbox').nth(1)
        first_category.click()

        # Select necessary topic
        page.get_by_text(topic_name, exact=True).get_by_role('checkbox').click()
        # Create assessment
        page.get_by_text('Create assessment', exact=True).click()
        # Start exam
        page.get_by_text('Start exam', exact=True).click(timeout=300_000)

        # Verify topic
        # Failsafe for cases when default selection was not removed.
        actual_topic = (
            page.
            locator('[class="text-base mt-1 font-medium truncate"]')
            .inner_text()
            .strip()
        )
        if topic_name != actual_topic:
            print(
                f'{datetime.now()}\t'
                f'Actual topic name is {actual_topic!r} instead of {topic_name!r}'
                )
            return False

        # Questions
        q1 = get_question_text(page)
        page.get_by_text('Next question', exact=True).click()
        q2 = get_question_text(page)
        page.get_by_text('Next question', exact=True).click()
        q3 = get_question_text(page)

        q_sets['q1'].add(q1)
        q_sets['q2'].add(q2)
        q_sets['q3'].add(q3)
        return True


def main() -> None:
    with (
        sync_playwright() as p,
        # Cannot get questions in headless mode
        p.chromium.launch(headless=False) as browser,
        browser.new_context(permissions=['microphone', 'camera']) as context,
        # Open an empty page to keep browser open
        context.new_page(),
        ):
        # Get existing topics
        with open_laba_ai(context) as page:
            topics = get_topics(page)

        # Load existing questions
        questions = read_existing_questions(QUESTIONS_FILE, topics)
        try:
            # Iterate over questions
            for category, category_dict in topics.items():
                if CATEGORIES and category not in CATEGORIES: continue

                for subcategory, topics in category_dict.items():
                    if SUBCATEGORIES and subcategory not in SUBCATEGORIES: continue

                    for topic_name in topics:
                        if TOPICS and topic_name not in TOPICS: continue

                        q_sets = questions[category][subcategory][topic_name]
                        for _ in range(TIMES_PER_TOPIC):
                            try:
                                record_questions(context, topic_name, q_sets)
                            except Error as e:
                                print(f'{datetime.now()}\t{e}')
        finally:
            save_questions(questions, QUESTIONS_FILE)


if __name__ == '__main__':
    with time_tracker():
        main()
