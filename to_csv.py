import csv
import json

from globals import Questions

INPUT_FILE = 'questions.json'
"""
Input JSON file.
"""

OUTPUT_FILE = 'questions.csv'
"""
Output CSV file.
"""

CATEGORY = 'Методы инженерии и анализа данных'
"""
Category to write into CSV file.
"""


def main() -> None:
    with open(INPUT_FILE) as f:
        data: Questions = json.load(f)
        to_write = data[CATEGORY]

    with open(OUTPUT_FILE, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, dialect='excel')
        for category, cat_dict in to_write.items():
            for topic, topic_dict in cat_dict.items():
                for question in topic_dict['q1']:
                    writer.writerow([category, topic, 2, question])

                for question in topic_dict['q2']:
                    writer.writerow([category, topic, 3, question])

                for question in topic_dict['q3']:
                    writer.writerow([category, topic, 4, question])


if __name__ == '__main__':
    main()
