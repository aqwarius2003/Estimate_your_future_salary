import requests
from terminaltables import AsciiTable
import os
from dotenv import load_dotenv
from itertools import count


def adds_three_zeros(specified_amount):
    """
       Корректирует указанную зарплату до ближайшей тысячи рублей, если это необходимо.

       Если specified_amount меньше 100, умножает его на 1000 для округления до ближайшей тысячи.
       Если specified_amount равно None, возвращает None.

       Аргументы:
           specified_amount (float or None): Зарплата, которую необходимо скорректировать.

       Возвращает:
           float or None: Скорректированная зарплата, округлённая до ближайшей тысячи рублей,
                          или None, если specified_amount равно None.
       """

    if specified_amount is None:
        return None
    return specified_amount * 1000 if specified_amount < 100 else specified_amount


def gets_average_value(salary_from, salary_to):
    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8
    return None


def predict_rub_salary_hh(vacancy):
    salary = vacancy.get('salary')
    if not salary or salary['currency'] != 'RUR':
        return None
    salary_from = salary.get('from')
    salary_to = salary.get('to')

    salary_from = adds_three_zeros(salary_from)
    salary_to = adds_three_zeros(salary_to)

    return gets_average_value(salary_from, salary_to)


def predict_rub_salary_sj(vacancy):
    salary_from = vacancy.get('payment_from')
    salary_to = vacancy.get('payment_to')
    currency = vacancy.get('currency')
    if currency != 'rub':
        return None
    return gets_average_value(salary_from, salary_to)


def get_vacancy_hh(language):
    hh_url = 'https://api.hh.ru/vacancies'

    hh_params = {
        'area': 1,  # Код Москвы
        'period': 30,  # Последний месяц
        'only_with_salary': True,  # Только вакансии с указанной зарплатой
        'per_page': 100,  # Количество вакансий на странице
        'page': 0,  # Номер страницы
        'text': f'программист {language}'
    }

    vacancies = []

    while True:
        response = requests.get(hh_url, params=hh_params)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            print(f'Не удалось сделать на hh запрос для языка {language}\n {err}')

            break
        vacancy_items = response.json()
        vacancies.extend(vacancy_items['items'])
        if not vacancy_items['items']:
            break
        hh_params['page'] += 1

    return vacancies


def get_vacancy_sj(sj_secret_key, language, page_number):
    sj_url = 'https://api.superjob.ru/2.0/vacancies/'
    sj_params = {
        'town': 4,  # Москва
        'catalogues': 48,  # Категория "Программирование, Разработка"
        'period': 0,
        'count': 100,  # Количество вакансий на странице
        'page': 0,  # Номер стартовой страницы
        'no_agreement': 1,  # Не показывать оклад «по договоренности»
        'keyword': f'{language}'
    }

    headers = {
        'X-Api-App-Id': sj_secret_key
    }
    sj_params.update({"page": page_number})
    response = requests.get(sj_url, headers=headers, params=sj_params)
    response.raise_for_status()

    vacancies_sj_per_page = response.json()
    return vacancies_sj_per_page


def get_vacancy_statistics_sj(sj_secret_key, language):
    salaries = []
    vacancies_found = None
    for page_number in count():
        try:
            jobs = get_vacancy_sj(sj_secret_key, language, page_number)
            vacancies = jobs.get('objects')

            for vacancy in vacancies:
                salary = predict_rub_salary_sj(vacancy)
                if salary:
                    salaries.append(salary)

            if not jobs.get('more'):
                vacancies_found = jobs.get('total')  # or get('total', 0) ?
                break
        except requests.exceptions.HTTPError as err:
            print(f'Не удалось сделать на sj запрос для языка {language}\n {err}')
            break

    vacancies_processed = len(salaries)
    average_salary = int(sum(salaries) / vacancies_processed) if vacancies_processed > 0 else 0

    vacancies_sj = {
        'Вакансий найдено': vacancies_found,
        'Вакансий обработано': vacancies_processed,
        'Средняя зарплата': average_salary
    }
    return vacancies_sj


def get_statistic_hh(vacancies):
    if vacancies:
        salaries = []
        for vacancy in vacancies:
            salary = predict_rub_salary_hh(vacancy)
            if salary is not None:
                salaries.append(salary)
        vacancies_found = len(vacancies)
        vacancies_processed = len(salaries)
        average_salary = int(sum(salaries) / vacancies_processed) if vacancies_processed else 0
        statistics = {
            'Вакансий найдено': vacancies_found,
            'Вакансий обработано': vacancies_processed,
            'Средняя зарплата': average_salary
        }
        return statistics
    else:
        return None


def create_vacancy_table(statistics):
    table_data = [
        ['Язык программирования', 'Вакансий найдено', 'Вакансий обработано', 'Средняя зарплата']
    ]

    for language, stats in statistics.items():
        row = [
            language, stats['Вакансий найдено'], stats['Вакансий обработано'], stats['Средняя зарплата']
        ]
        table_data.append(row)

    table = AsciiTable(table_data)
    return table.table


def main():
    languages = ['c#', 'python', 'c++', 'java', 'javascript', 'php', 'c', 'go', 'rust', 'ruby']

    all_vacancies_hh = {}
    all_vacancies_sj = {}
    load_dotenv()
    sj_secret_key = os.getenv('SJ_SECRET_KEY')

    for language in languages:
        statistics_hh = get_statistic_hh(get_vacancy_hh(language))
        if statistics_hh:
            all_vacancies_hh[language] = statistics_hh

        statistics_sj = get_vacancy_statistics_sj(sj_secret_key, language)
        if statistics_sj:
            all_vacancies_sj[language] = statistics_sj

    table_hh = create_vacancy_table(all_vacancies_hh)
    table_sj = create_vacancy_table(all_vacancies_sj)

    print(f'Статистика с HH\n{table_hh}')
    print(f'\nСтатистика с SuperJobs\n{table_sj}')


if __name__ == "__main__":
    main()
