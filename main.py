import requests
from terminaltables import AsciiTable
import os
from dotenv import load_dotenv
from itertools import count
# import logging

# logging.basicConfig(level=logging.DEBUG)
# logging.getLogger('requests').setLevel(logging.DEBUG)

languages = ['C#', 'Python', 'C++', 'Java', 'JavaScript', 'PHP', 'C', 'Go', 'Rust', 'Kotlin']

HH_URL = 'https://api.hh.ru/vacancies'
hh_params = {
    'area': 1,  # Код Москвы
    'period': 30,  # Последний месяц
    'only_with_salary': True,  # Только вакансии с указанной зарплатой
    'per_page': 100,  # Количество вакансий на странице
    'page': 0  # Номер страницы
}


SJ_URL = 'https://api.superjob.ru/2.0/vacancies/'
sj_params = {
    'town': 4,  # Москва (4)
    'catalogues': 48,  # Категория "Программирование, Разработка"
    'count': 5,  # Количество вакансий на странице
    'page': 0,  # Номер стартовой страницы
    'no_agreement': 1  # Не показывать оклад «по договоренности»
}


# Дополнительная функция, поправляет значение указанной зарплаты до тысяч рублей (на HH много двузначных зарплат)
def adds_three_zeros(specified_amount):
    if specified_amount is None:
        return None  # Возвращаем None, если на входе None
    elif specified_amount < 100:
        return specified_amount * 1000
    else:
        return specified_amount


def predict_rub_salary(vacancy, source):
    if source == 'hh':
        salary = vacancy.get('salary')
        if not salary or salary['currency'] != 'RUR':
            return None
        salary_from = salary.get('from')
        salary_to = salary.get('to')

    elif source == 'sj':
        salary_from = vacancy.get('payment_from')
        salary_to = vacancy.get('payment_to')
        currency = vacancy.get('currency')
        if currency != 'rub':
            return None

    salary_from = adds_three_zeros(salary_from)
    salary_to = adds_three_zeros(salary_to)

    if salary_from and salary_to:
        return (salary_from + salary_to) / 2
    elif salary_from:
        return salary_from * 1.2
    elif salary_to:
        return salary_to * 0.8

    return None


def get_vacancy_statistics_hh(language):
    hh_params['page'] = 0
    hh_params['text'] = f'программист {language}'
    vacancies = []

    while True:
        response = requests.get(HH_URL, params=hh_params)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            break
        data = response.json()
        vacancies.extend(data['items'])
        if not data['items']:  # Если кончились вакансии на странице
            break
        hh_params['page'] += 1

    return vacancies


def get_vacancy_statistics_sj(language):
    load_dotenv()
    sj_secret_key = os.getenv('SJ_SECRET_KEY')
    vacancies_sj = []
    sj_params['keyword'] = f'{language}'
    for page in count():
        sj_params.update({"page": page})
        headers = {
            'X-Api-App-Id': sj_secret_key
        }
        response = requests.get(SJ_URL, headers=headers, params=sj_params)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError:
            continue
        response_data = response.json()
        vacancies_sj.extend(response_data['objects'])
        if not response_data["more"]:
            break

    return vacancies_sj


def get_statistic(vacancies, source):
    if vacancies:
        salaries = []
        for vacancy in vacancies:
            salary = predict_rub_salary(vacancy, source)
            if salary is not None:
                salaries.append(salary)
        vacancies_found = len(vacancies)
        vacancies_processed = len(salaries)
        average_salary = int(sum(salaries) / vacancies_processed) if vacancies_processed > 0 else 0
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
    all_vacancies_hh = {}
    all_vacancies_sj = {}

    for language in languages:
        statistics_hh = get_statistic(get_vacancy_statistics_hh(language), 'hh')
        statistics_sj = get_statistic(get_vacancy_statistics_sj(language), 'sj')
        if statistics_hh:
            all_vacancies_hh[language] = statistics_hh
        if statistics_sj:
            all_vacancies_sj[language] = statistics_sj

    table_hh = create_vacancy_table(all_vacancies_hh)
    table_sj = create_vacancy_table(all_vacancies_sj)

    print('Статистика с HH\n' + table_hh)
    print('Статистика с SuperJobs\n' + table_sj)


if __name__ == "__main__":
    main()
