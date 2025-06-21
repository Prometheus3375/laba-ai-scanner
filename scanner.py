import json
import tomllib
from collections import defaultdict
from datetime import datetime
from typing import Any, TypedDict

from playwright.sync_api import BrowserContext, Error, Page, expect, sync_playwright

CONFIG_FILE = 'config.toml'
"""
Path to a configuration file with login information.
"""

QUESTIONS_FILE = 'questions.json'
"""
Path to a file with questions.
"""

CATEGORY = 'Методы инженерии и анализа данных'
"""
Which category to scan. Can be set to ``None`` to scan all of them.
"""

TIMES_PER_TOPIC = 30
"""
How many times scan every topic.
"""


def open_laba_ai(context: BrowserContext, /) -> Page:
    """
    Opens Laba.AI platform and logs in.
    """
    with open(CONFIG_FILE, 'rb') as f:
        config = tomllib.load(f)

    page = context.new_page()
    page.goto(config['url'])
    page.get_by_placeholder('Name Surname', exact=True).fill(config['full_name'])
    emails = page.get_by_placeholder('Use corporate email address only', exact=True)
    emails.first.fill(config['email'])
    emails.last.fill(config['coordinator_email'])
    page.get_by_text('Verify', exact=True).click()
    return page


class QuestionSets(TypedDict):
    q1: set[str]
    q2: set[str]
    q3: set[str]


type Questions = dict[str, dict[str, dict[str, QuestionSets]]]


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
    return (
        page
        .locator('[class*="text-sm text-balance select-none pointer-events-none"]')
        .inner_text()
    )


def record_questions(context: BrowserContext, topic_name: str, q_sets: QuestionSets, /) -> None:
    """
    Opens Laba.AI, resets topic selection, selects the given topic and starts an exam.
    Then records questions encountered to the given ``q_sets``.
    """
    with open_laba_ai(context) as page:
        # Resets default selection by clicking the checkbox twice.
        # .check() or .unchecck() do not work here as this checkbox is in a mixed state.
        # They also often throw an error for an unknown reason when used of the first category.
        main_checkbox = page.get_by_role('checkbox').first
        main_checkbox.click()
        main_checkbox.click()

        # Select necessary topic name
        page.get_by_text(topic_name, exact=True).get_by_role('checkbox').check()
        # Create assessment
        page.get_by_text('Create assessment', exact=True).click()
        # Start exam
        page.get_by_text('Start exam', exact=True).click()

        # Questions
        q1 = get_question_text(page)
        page.get_by_text('Next question', exact=True).click()
        q2 = get_question_text(page)
        page.get_by_text('Next question', exact=True).click()
        q3 = get_question_text(page)

        q_sets['q1'].add(q1)
        q_sets['q2'].add(q2)
        q_sets['q3'].add(q3)


def main() -> None:
    with (
        sync_playwright() as p,
        # Cannot get questions in headless mode
        p.chromium.launch(headless=False) as browser,
        browser.new_context(permissions=['microphone', 'camera']) as context,
        ):
        # Get existing topics
        with open_laba_ai(context) as page:
            topics = get_topics(page)

        # Load existing questions
        questions = read_existing_questions(QUESTIONS_FILE, topics)
        try:
            # Iterate over questions
            for category, category_dict in questions.items():
                if CATEGORY and category != CATEGORY: continue

                for subcategory, subcat_dict in category_dict.items():
                    for topic_name, q_sets in subcat_dict.items():
                        for _ in range(TIMES_PER_TOPIC):
                            try:
                                record_questions(context, topic_name, q_sets)
                            except Error as e:
                                print(f'{datetime.now()}    {e}')
        finally:
            save_questions(questions, QUESTIONS_FILE)


if __name__ == '__main__':
    main()
