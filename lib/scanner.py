import json
from collections import defaultdict
from logging import Logger, getLogger
from threading import Event, Thread
from typing import Any

from playwright.sync_api import BrowserContext, Error, Page, expect, sync_playwright

from lib.configs import ScannerConfig
from lib.globals import QuestionSets, Questions

logger = getLogger('scanner')

type TopicHierarchy = dict[str, dict[str, list[str]]]


def open_laba_ai(context: BrowserContext, config: ScannerConfig, /) -> Page:
    """
    Opens Laba.AI platform and logs in.
    """
    page = context.new_page()
    page.goto(config.url)
    page.get_by_placeholder('Name Surname', exact=True).fill(config.full_name)
    emails = page.get_by_placeholder('Use corporate email address only', exact=True)
    emails.first.fill(config.email)
    emails.last.fill(config.coordinator_email)
    page.get_by_text('Verify', exact=True).click()
    return page


def get_topics(page: Page, /) -> TopicHierarchy:
    """
    Extracts topic hierarchy from the page.
    """
    topics = defaultdict(lambda: defaultdict(list))
    locator = page.get_by_role('checkbox')
    expect(locator.first).to_be_visible(timeout=60_000)

    for i in range(locator.count()):
        box = locator.nth(i)
        value = box.get_attribute('value')
        if value:
            major, minor, topic = value.split('___', maxsplit=2)
            topics[major][minor].append(topic)

    return topics


def read_existing_questions(filepath: str, topics: TopicHierarchy, /) -> Questions:
    """
    Reads the given JSON with recorded questions, adds missing topics
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
    # Some questions are identically the same, but use 'е' instead of 'ё'.
    # Better to replace 'ё' completely to avoid trivial duplicates.
    text = text.replace('ё', 'е').strip('.')
    text = ' '.join(text.split())
    return text


def record_questions(
        context: BrowserContext,
        config: ScannerConfig,
        topic: str,
        q_sets: QuestionSets,
        /,
        ) -> bool:
    """
    Opens Laba.AI, resets topic selection, selects the given topic and starts an exam.
    Then records questions encountered to the given ``q_sets``.
    Returns ``True`` on success and ``False`` otherwise.
    """
    with open_laba_ai(context, config) as page:
        # .check() or .uncheck() do not work on the first checkbox as it is in a mixed state.
        # They also sometimes throw an error for an unknown reason.
        # https://github.com/microsoft/playwright/issues/13470

        # Wait until first category checkbox becomes visible
        first_category_checkbox = page.get_by_role('checkbox').nth(1)
        expect(first_category_checkbox).to_be_visible(timeout=60_000)
        # Remove default selection by clicking the first category
        first_category_checkbox.click()

        # Select necessary topic
        page.get_by_text(topic, exact=True).get_by_role('checkbox').click()
        # Create assessment
        page.get_by_text('Create assessment', exact=True).click()
        # Start exam
        page.get_by_text('Start exam', exact=True).click(timeout=300_000)

        # Verify topic
        # Failsafe for cases when default selection was not removed.
        actual_topic = (
            page
            .locator('[class="text-base mt-1 font-medium truncate"]')
            .inner_text()
            .strip()
        )
        if topic != actual_topic:
            logger.warning(
                f'Actual topic name is {actual_topic!r} instead of {topic!r}; '
                f'aborting this record attempt'
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


def scan(config: ScannerConfig, stop_event: Event, /) -> None:
    """
    Starts scanning Laba.AI. Gracefully stops if at some point the given event is set.
    """
    logger.info('Starting the scanner...')

    questions_filepath = config.output_filepath
    categories = config.categories
    subcategories = config.subcategories
    topics = config.topics
    times_per_topic = config.times_per_topic

    with (
        sync_playwright() as p,
        # Cannot get questions in headless mode
        p.chromium.launch(handle_sigint=False, headless=False) as browser,
        browser.new_context(permissions=['microphone', 'camera']) as context,
        # Open an empty page to keep browser open
        context.new_page(),
        ):
        logger.info('Getting existing topic hierarchy on the site')
        with open_laba_ai(context, config) as page:
            topic_hierarchy = get_topics(page)

        if stop_event.is_set():
            logger.info('The scanner is stopped')
            return

        logger.info(f'Loading questions stored locally in {questions_filepath}')
        questions = read_existing_questions(questions_filepath, topic_hierarchy)

        logger.info('The scanner is started. You can minimize the browser')
        try:
            # Iterate over existing topic hierarchy
            for category, category_dict in topic_hierarchy.items():
                if categories and category not in categories: continue

                for subcategory, topic_list in category_dict.items():
                    if subcategories and subcategory not in subcategories: continue

                    for topic in topic_list:
                        if topics and topic not in topics: continue

                        q_sets = questions[category][subcategory][topic]
                        success_times = 0
                        while success_times < times_per_topic:
                            # Exit immediately if the event is set
                            if stop_event.is_set(): return

                            try:
                                success = record_questions(context, config, topic, q_sets)
                            except Error as e:
                                logger.exception(str(e))
                            else:
                                success_times += success

        finally:
            logger.info(f'Saving recorded questions to {questions_filepath!r}')
            save_questions(questions, questions_filepath)
            logger.info('The scanner is stopped')


class Scanner:
    """
    A class for scanning Laba.AI website for questions.
    """
    __slots__ = 'config', '_thread', '_stop_event', '_is_running'

    def __init__(self, config: ScannerConfig, /) -> None:
        self.config = config
        self._thread: Thread | None = None
        self._stop_event: Event | None = None
        self._is_running = False

    @property
    def logger(self, /) -> Logger:
        """
        Logger of this instance.
        """
        return logger

    @property
    def is_running(self, /) -> bool:
        """
        Whether this instance is running.
        """
        return self._is_running

    def start(self, /) -> None:
        """
        Starts this scanner.
        """
        if self._is_running: return

        self._is_running = True
        self._thread = Thread(target=self._thread_target, name='scanner', daemon=True)
        self._stop_event = Event()
        self._thread.start()

    def stop(self, /) -> None:
        """
        Stops this scanner.
        """
        if self._is_running:
            if not self._stop_event.is_set():
                logger.info('Stopping the scanner...')
                self._stop_event.set()

            self._thread.join()

    def _thread_target(self, /) -> None:
        scan(self.config, self._stop_event)

        self._thread = None
        self._stop_event = None
        self._is_running = False


__all__ = 'Scanner',
