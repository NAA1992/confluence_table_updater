from atlassian import Confluence
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import os
import sys
import requests
import inspect

# from .libraries.harbor_tool import harbor_class


class ConfluenceTableUpdater:
    #MARK: ConfluenceTableUpdater
    def __init__(self):
        # Таблица имеет вид
        # | Заголовок |
        # | col1 | col2 | col3 ...
        # | val1 | val2 | val3 ...
        # ...
        # | Следующий заголовок |
        # | col1 | col2 | col3 ...
        # | val1 | val2 | val3 ...
        # ...
        
        # Связь наименования параметра в окружении с переменной в Python
        self.environments = {}
        self.num_critical_params = 7 # Количество критически важных ключей в self.environments
        

        # Данные для подключения к Confluence
        self.environments["CONFLUENCE_URL"] = None
        self.environments["CONFLUENCE_LOGIN"] = None
        self.environments["CONFLUENCE_PASSWORD"] = None
        
        # Данные, которые будут записаны в таблицу (колонки)
        self.environments["PACKAGE_HEADER"] = None # Заголовок в таблице. Обязательное
        self.environments["PACKAGE_NAME"] = None # Имя пакета (ключевое поле)
        self.environments["PACKAGE_VERSION"] = None # Версия пакета (ключевое поле)
        self.environments["PACKAGE_HARBOR"] = None # Ссылка на Harbor пакета. Обязательное поле
        
        # Отделил, т.к. ниже идут уже не критически важные параметры
        self.environments["PACKAGE_NEXUS"] = None # Ссылка на Nexus пакета
        
        # Параметры, получаемые из окружения для SONAR
        self.environments["SONAR_FLAG"] = None # Флаг, что нужно добавлять еще Sonar баннеры (скан исходников)
        self.environments["SONAR_CONFIG_PATH"] = "./" # Путь до папки с настройками sonar проекта


        self.sonar_filename = 'sonar-project.properties' # наименование файла с настройками sonar проекта
        self.sonar_banners = None
        
        # номер колонки. Нумерация начинается с 0
        self.numcell_package_name = 0
        self.numcell_package_version = 1
        self.numcell_package_nexus = 4
        self.numcell_package_harbor = 3
        self.numcell_sonar_banners = 5
        

    
    def get_environment_params(self):
        #MARK: get_environment_params
        # Получение значений из переменных окружения
        for envName, value in self.environments.items():
            envValue = os.getenv(envName, '')
            self.environments[envName] = envValue
            # Для Nexus ссылки создаем тег <a> (гиперссылку в HTML)
            if envName == 'PACKAGE_NEXUS' and envValue:
                envValue = BeautifulSoup('<a href="{url}">{text}</a>'.format(url=package_nexus, text=package_nexus), 'html.parser')
                self.environments[envName] = envValue
            # Для пути к Sonar папке создаем абсолютный путь
            elif envName == 'SONAR_CONFIG_PATH':
                envValue = os.path.abspath(envValue)
                self.environments[envName] = envValue
        

    def getenv_case_insensitive(self, var_name):
        #MARK: getenv_case_insensitive
        # Функция для поиска переменной в окружении в любых регистрах
        # Преобразуем имя переменной в нижний регистр для поиска
        var_name_lower = var_name.lower()
        
        # Проходим по всем переменным окружения и сравниваем их имена в нижнем регистре
        for key, value in os.environ.items():
            if key.lower() == var_name_lower:
                return value
        return None

    def check_important_environments(self):
        #MARK: check_important_environments
        # Проверяем переменные окружения на заполняемость. 
        # Значения не должны быть пустыми, а так же все переменные должны быть объявлены
        all_is_good = True
        for i, envName, value in (range(self.num_critical_params), self.environments.items()):
            if not value:
                print(f"Установите переменную окружения {envName}")
                all_is_good = False
        return all_is_good
          
        

    def read_sonar_properties(self):
        fullname_of_file = os.path.join(sonar_path, sonar_filename)
        
        # Проверяем, что файл существует рядом с исполняемым скриптом
        if not os.path.exists(fullname_of_file):
            raise FileNotFoundError(f"Файл '{fullname_of_file}' не найден.")

        # Инициализируем переменные для хранения значений
        project_key = None
        host_url = None
        login = None

        try:
            # Открываем файл и читаем построчно
            with open(fullname_of_file, 'r', encoding='utf-8') as f:
                for line in f:
                    # Убираем пробелы в начале и в конце строки
                    line = line.strip()
                    
                    # Проверяем, начинается ли строка с нужных параметров
                    if line.startswith('sonar.projectKey='):
                        project_key = line.split('=', 1)[1].strip()
                    elif line.startswith('sonar.host.url='):
                        host_url = line.split('=', 1)[1].strip()
                    elif line.startswith('sonar.login='):
                        login = line.split('=', 1)[1].strip()
                    if all([project_key, host_url, login]):
                        break

            # Проверяем, что все значения найдены и не пустые
            if not all([project_key, host_url, login]):
                raise ValueError("Не удалось найти все необходимые параметры или они пустые.")
            
            # Возвращаем найденные значения
            return project_key, host_url, login

        except FileNotFoundError as e:
            print(f"Ошибка: {e}")
        except ValueError as e:
            print(f"Ошибка: {e}")
        except Exception as e:
            print(f"Неизвестная ошибка: {e}")


if __name__ == "__main__":
    #MARK: MAIN

    
    
    
    
    # Собираем все переменные окружения в DICT для дальнейшей обработки
    env_data = {name_num_cell: package_name
                , version_num_cell: package_version
                , nexus_num_cell: package_nexus
                , harbor_num_cell: package_harbor}
    # Если есть sonar_flag, будем пытаться открыть sonar-project.properties и построить на основе его баннеры
    if sonar_flag:
        # [![Статус порога качества](https://sonar.example.com/api/project_badges/measure?project=projectKey_example&metric=alert_status&token=HASH_LOGIN_PASS)]https://sonar.example.com/dashboard?id=projectKey_example)
        sonar_metrics_urls = []
        metrics = {
            "alert_status": "Статус порога качества"
            , "bugs": "Ошибки"
            }
        sonar_properties = read_sonar_properties()
        if sonar_properties:
            project_key, host_url, login = sonar_properties
            for eng_metr, ru_metr in metrics.items():
                url_metric_markdown = f"{host_url}/api/project_badges/measure?project={project_key}&metric={eng_metr}&token={login}"
                url_dashboard_markdown = f"{host_url}/dashboard?id={project_key}"
                metric_html = f'<a href="{url_dashboard_markdown}"><img src="{url_metric_markdown}" alt="{ru_metr}"></a>'
                sonar_metrics_urls.append(metric_html)
                # sonar_metrics_urls[ru_metr] = {url_dashboard_markdown: url_metric_markdown}
                # final_markdown = f"[![{ru_metr}]({url_metric_markdown})]({url_dashboard_markdown})"
            sonar_metrics_urls_string = "".join(sonar_metrics_urls)
            sonar_html_content = BeautifulSoup(sonar_metrics_urls_string, 'html.parser')  # Парсим строку HTML в объект
            env_data[sonar_num_cell] = sonar_html_content
            # env_data[sonar_num_cell] = sonar_metrics_urls
        else:
            sonar_flag = False
        

        
        
    # Исходя из нумерации колонок для каждого значения, понимаем, сколько минимум колонок должно быть в таблице
    minimum_cells_in_table = max(list(env_data.keys())) + 1
    
    # Проверяем обязательность заполнений всех нужных Environments
    if not check_important_environments():
        sys.exit(1)

    # Пример URL: https://conf.digitalms.ru/pages/viewpage.action?pageId=88429727
    # Разбираем URL на компоненты
    parsed_url = urlparse(confluence_url)
    # Извлекаем домен
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    # Извлекаем параметр pageId
    query_params = parse_qs(parsed_url.query)
    page_id = query_params.get('pageId', [None])[0]

    

    try:
        # Подключение к Confluence
        confluence = Confluence(
            url=domain,
            username=confluence_login,
            password=confluence_password  # Можно использовать API-токен вместо пароля
        )

        # Получение содержимого страницы
        page = confluence.get_page_by_id(page_id, expand='body.storage')
        if not page:
            raise ValueError(f"Страница с ID {page_id} не найдена или недоступна.")
        
        # Извлечение текущего HTML-содержимого страницы
        page_content = page['body']['storage']['value']

    except requests.exceptions.ConnectionError as e:
        print("Не удалось подключиться к URL Confluence. Проверьте URL или интернет-соединение.")
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при подключении к Confluence: {e}")
        sys.exit(1)
        

    try:
        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(page_content, 'html.parser')

        # Ищем все заголовки таблиц (HEADER)
        table_headers = soup.find_all(lambda tag: 
                                    tag.name in ['h4'] and 
                                    package_header in tag.get_text() and 
                                    tag.find_parent('table') is not None)
        if not table_headers:
            raise ValueError(f"Не найден заголовок '{package_header}'.")
        if len(table_headers) > 1:
            raise ValueError(f"Обнаружено несколько заголовков '{package_header}'. Мы не знаем с чем работать, прерываем работу")
        # Для примера можно вывести первую таблицу
        # if table_headers:
        #    print(table_headers[0].prettify())
        # По идее header должен быть найден только один
        table_header = table_headers[0]
        
        # Ищем родительский элемент <td>, чтобы точно определить, что заголовок связан с таблицей
        table_header_td = table_header.find_parent('td')
        if not table_header_td:
            raise ValueError(f"Не найден <td> для заголовка '{package_header}'.")

        # Ищем таблицу, которая содержится в этом же родительском <tr>
        table_body = table_header_td.find_parent('table')
        if not table_body:
            raise ValueError(f"Таблица после заголовка '{package_header}' не найдена.")

        # Ищем следующий заголовок, чтобы вставить строку перед ним
        next_header = table_header_td.find_next(lambda tag: tag.name in ['h4'] and package_header not in tag.get_text())
        #next_header = table_body.find_next(lambda tag: tag.name in ['h4'])
        # Если next_header найден и он совпадает с package_header, ищем следующий
        #while next_header and package_header in next_header.get_text():
        #    next_header = next_header.find_next(lambda tag: tag.name in ['h4'])

    except ValueError as ve:
        print(f"Ошибка при обработке страницы: {ve}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка при парсинге HTML: {e}")
        sys.exit(1)



    try:
        found_row = None
        rows = table_body.find_all('tr')
        # Определить количество столбцов по первой строке с ячейками <td>
        column_count = len(rows[1].find_all('td'))  # Предполагается, что заголовок таблицы идет первым, а вторым уже "тело" (заголовки колонок)
        if column_count < minimum_cells_in_table:
            raise ValueError(f"Было обнаружено, что в найденной таблице меньше ячеек, чем нужно ({minimum_cells_in_table}). Обновление прервано")
        
        # Собираем все строки до следующего заголовка (если он есть)
        rows_to_check = []
        for row in rows:
            if next_header and row == next_header.find_previous('tr'):
                break  # Останавливаем поиск, если дошли до следующего заголовка
            rows_to_check.append(row)
        
        # Перебираем строки, ищем только нужную
        for row in rows_to_check:
            cells = row.find_all('td')
            if len(cells) >= minimum_cells_in_table:
                # Проверяем имя пакета и версию его
                name_cell = cells[name_num_cell].text.strip()
                version_cell = cells[version_num_cell].text.strip()
                if name_cell == package_name and version_cell == package_version:
                    found_row = row
                    break

        if found_row:
            # Обновляем ячейки, если строка найдена
            cells = found_row.find_all('td')
            # Парсим колонку с Nexus ссылкой, вытаскиваем из <td> (тега таблицы)
            current_nexus_cell = BeautifulSoup(str(cells[nexus_num_cell]), 'html.parser')
            if current_nexus_cell.td:
                current_nexus_cell = current_nexus_cell.td.decode_contents()
            
            # Сравниваем строки Nexus, Harbor, Sonar
            if str(current_nexus_cell) == str(package_nexus) and cells[harbor_num_cell].string == package_harbor:
                if sonar_num_cell in env_data:
                    # Парсим колонку с SonarQube, вытаскиваем из <td> (тега таблицы)   
                    current_sonar_cell = BeautifulSoup(str(env_data[sonar_num_cell]), 'html.parser')
                    if current_sonar_cell.td:
                        current_sonar_cell = str(current_sonar_cell.td.decode_contents())
                    else:
                        current_sonar_cell = str(current_sonar_cell)
                    # Извлекаем содержимое для expected
                    expected_sonar = str(env_data[sonar_num_cell])
                    # Сравниваем текстовое содержимое обоих объектов
                    if current_sonar_cell.strip() == expected_sonar.strip():
                        print("Нет необходимости обновлять Confluence - информация уже занесена")
                        sys.exit(0)
                else:
                    print("Нет необходимости обновлять Confluence - информация уже занесена")
                    sys.exit(0)

            # Заменяем содержимое ячейки на гиперссылку
            cells[nexus_num_cell].string = ''  # Очищаем содержимое. Можно использовать .clear() как показано ниже
            cells[nexus_num_cell].append(env_data[nexus_num_cell])
            # Harbor текстом обычным вставляем
            cells[harbor_num_cell].string = env_data[harbor_num_cell]
            # Sonar наподобие nexus, только здесь не гиперссылка, а плашки Sonar
            if sonar_num_cell in env_data:
                cells[sonar_num_cell].clear()  # Очищаем содержимое ячейки перед вставкой
                cells[sonar_num_cell].append(env_data[sonar_num_cell])  # Добавляем HTML как дочерний элемент
                
        else:
            # Создаем новую строку, если строка не найдена
            new_row = soup.new_tag('tr')
            
            for i in range(column_count):
                new_row.append(soup.new_tag('td'))
                if i in env_data:
                    if i in [sonar_num_cell, nexus_num_cell]:
                        new_row.contents[i].append(env_data[i])  # Добавляем HTML как дочерний элемент
                    else:
                        new_row.contents[i].string = env_data[i]
            
            # Вставляем строку перед следующим заголовком или в конец таблицы
            if next_header:
                # Вставляем перед заголовком
                next_header.find_previous('tr').insert_before(new_row)
                #table_body.insert_before(new_row, next_header.find_previous('tr'))
            else:
                # Добавляем в конец, если других заголовков нет
                table_body.append(new_row)


        # Блок работы с Harbor. Передаем ссылку на имэдж, вытаскиваем отчет о скане уязвимостей
        #try:
        #    harbor = harbor_class(package_harbor, confluence_login, confluence_password) # Логин и пароль от Harbor
        #    filepath_csv_with_reports_scan = harbor.export_csv_report()
        #except Exception as e:
        #    print(e)
        #    pass

        # Получение обновленного HTML
        updated_html = str(soup)

        # Обновление страницы с новым содержимым
        confluence.update_page(
            page_id=page_id,
            title=page['title'],
            body=updated_html
        )

        print("Страница обновлена успешно!")

    except Exception as e:
        print(f"Ошибка при обновлении таблицы: {e}")
        sys.exit(1)
        
import os
print(os.path.abspath(''))