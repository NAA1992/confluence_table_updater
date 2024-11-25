from atlassian import Confluence
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import os
from typing import Union, Tuple





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
            # from_env - флаг получения данных из окружения
            # num_column - номер колонки, куда будут записаны данные в таблице. Нумерация начинается с 0
            # value - значение по умолчанию.
            # is_required - флаг обязательности заполнения поля
            # is_key - ключевое поле в таблице
        self.environments = {
            # Данные для подключения к Confluence
            "CONFLUENCE_URL": {"from_env": True, "num_column": None
                               , "value": None, "is_required": True, "is_key": False}
            , "CONFLUENCE_LOGIN": {"from_env": True, "num_column": None
                                   , "value": None, "is_required": True, "is_key": False}
            , "CONFLUENCE_PASSWORD": {"from_env": True, "num_column": None
                                      , "value": None, "is_required": True, "is_key": False}
            # Данные, которые будут записаны в таблицу (колонки)
            , "PACKAGE_HEADER": {"from_env": True, "num_column": None
                                 , "value": None, "is_required": True} # Заголовок в таблице. Обязательное
            , "PACKAGE_NAME": {"from_env": True, "num_column": 0
                               , "value": None, "is_required": True, "is_key": True} # Имя пакета (ключевое поле)
            , "PACKAGE_VERSION": {"from_env": True, "num_column": 1
                                  , "value": None, "is_required": True, "is_key": True} # Версия пакета (ключевое поле)
            , "PACKAGE_HARBOR": {"from_env": True, "num_column": 3
                                 , "value": None, "is_required": True, "is_key": False} # Ссылка на Harbor пакета. Обязательное поле
            #### Отделил, т.к. ниже идут необязательные параметры для скрипта
            , "PACKAGE_NEXUS": {"from_env": True, "num_column": 4
                                , "value": None, "is_required": False, "is_key": False} # Ссылка на Nexus пакета
            , "SONAR_DATA": {"from_env": False, "num_column": 5
                             , "value": None, "is_required": False, "is_key": False} # SONAR данные (баннеры)
            # Параметры, получаемые из окружения для SONAR
            , "SONAR_FLAG": {"from_env": True, "num_column": None
                             , "value": False, "is_required": False, "is_key": False} # Флаг, что нужно добавлять еще Sonar баннеры (скан исходников)
            , "SONAR_CONFIG_PATH": {"from_env": True, "num_column": None
                                    , "value": "./", "is_required": False, "is_key": False} # Путь до папки с настройками sonar проекта
            }

        self.sonar_filename = 'sonar-project.properties' # наименование файла с настройками sonar проекта



    def get_environment_params(self) -> None:
        #MARK: get_environment_params
        # Получение значений из переменных окружения
        for varName, varDict in self.environments.items():
            if varDict.get("from_env", False):
                envValue = os.getenv(varName, varDict.get("value", ''))
                varDict["value"] = envValue
                # Доп. обработки для каждого из наименования переменных окружения
                # Для Nexus ссылки создаем тег <a> (гиперссылку в HTML)
                if varName == 'PACKAGE_NEXUS' and envValue:
                    envValue = BeautifulSoup('<a href="{url}">{text}</a>'.format(url=envValue, text=envValue), 'html.parser')
                    varDict["value"] = envValue
                # Для пути к Sonar папке создаем абсолютный путь
                elif varName == 'SONAR_CONFIG_PATH':
                    envValue = os.path.abspath(envValue)
                    varDict["value"] = envValue
                elif varName == 'SONAR_FLAG':
                    envValue = envValue.lower().strip() == 'true'
                    varDict["value"] = envValue


    def check_important_environments(self) -> bool:
        #MARK: check_important_environments
        # Проверяем переменные окружения на заполняемость.
        all_is_good = True
        for varName, varDict in self.environments.items():
            if varDict.get("is_required", False) == True and not varDict.get("value", None):
                print(f"Установите переменную окружения {varName}")
                all_is_good = False
        return all_is_good


    def extract_data_for_columns(self) -> dict:
        #MARK: calc_count_columns
        data_for_columns = {}
        for varName, varDict in self.environments.items():
            if isinstance(varDict["num_column"], int):
                data_for_columns[varName] = varDict
        return data_for_columns



    def read_sonar_properties(self) -> Union[Tuple[str, str, str]] | None:
        #MARK: read_sonar_properties
        fullname_of_file = os.path.join(self.environments["SONAR_CONFIG_PATH"]["value"], self.sonar_filename)

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

    def conluence_obj_and_pageId(self) -> Union[Tuple[Confluence, str]]:
        #MARK: conluence_obj_and_pageId
        # Пример URL: https://conf.digitalms.ru/pages/viewpage.action?pageId=88429727
        # Разбираем URL на компоненты
        parsed_url = urlparse(self.environments["CONFLUENCE_URL"]["value"])
        # Извлекаем домен
        domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        # Извлекаем параметр pageId
        query_params = parse_qs(parsed_url.query)
        page_id = query_params.get('pageId', [None])[0]

        # Подключение к Confluence
        confluence = Confluence(
            url=domain,
            username=self.environments["CONFLUENCE_LOGIN"]["value"],
            password=self.environments["CONFLUENCE_PASSWORD"]["value"]  # Можно использовать API-токен вместо пароля
        )
        return (confluence, page_id)

    def update_cell_in_html_table(self, cells, dict_with_values):
        #MARK: update_cell_in_html_table
        if isinstance(dict_with_values["value"], BeautifulSoup):
            cells[dict_with_values["num_column"]].clear() # Очищаем содержимое ячейки перед вставкой
            cells[dict_with_values["num_column"]].append(dict_with_values["value"]) # Добавляем HTML как дочерний элемент
        else: # Иначе вставляем содержимое обычным текстом
            cells[dict_with_values["num_column"]].string = dict_with_values["value"]
        return cells


    def modify_html(self, page_content:str) -> str | None:
        #MARK: modify_html
        # Парсим страницу, находим таблицу и заголовок
        try:
            package_header = self.environments["PACKAGE_HEADER"]["value"]
            # Парсим HTML с помощью BeautifulSoup
            soup = BeautifulSoup(page_content, 'html.parser')

            # Ищем все заголовки таблиц (HEADER) + фильтр на нужное нам имя заголовка
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

        except ValueError as ve:
            raise ValueError(f"Ошибка при обработке страницы: {ve}")
        except Exception as e:
            raise Exception(f"Неожиданная ошибка при парсинге HTML: {e}")


        ### Из распарсенной таблицы ищем колонку, где будем вставлять \ изменять информацию
        # Считаем количество колонок, куда будут вставляться данные
        cells_for_insert = self.extract_data_for_columns()
        # Считаем не на основе количества вставляем объектов
        # num_cells_for_insert = len(cells_for_insert)
        # А на основе максимального значения номера колонки, куда будет вставляться контент
        num_cells_for_insert = 1
        for insDict in cells_for_insert.values():
            # Не забываем, что номера колонок начинаются с 0
            num_cells_for_insert = max(num_cells_for_insert, insDict["num_column"] + 1)

        # Флаг для определения начала и окончания сбора строк
        collect_rows = False
        # Список строк между заголовками
        rows_between_headers = []
        # Начинаем сбор строк только начиная от найденного заголовка
        for row in table_body.find_all('tr'):
            # Если текущая строка содержит заголовок package_header, включаем сбор
            if not collect_rows and table_header in row.find_all():
                collect_rows = True
                continue
            elif collect_rows:
                # Если встречаем следующий заголовок, заканчиваем сбор
                if next_header and next_header in row.find_all():
                    break
                # Иначе собираем строки для дальнейшей обработки
                rows_between_headers.append(row)
        # Определить количество столбцов по первой строке с ячейками <td>
        column_count = len(rows_between_headers[0].find_all('td'))
        if column_count < num_cells_for_insert:
            raise ValueError(f"Было обнаружено, что в найденной таблице меньше ячеек, чем нужно ({num_cells_for_insert}). Обновление прервано")
        # Предполагается, что после заголовка таблицы, идут заголовки к колонкам, поэтому начинаем работать со 2 строки
        rows_between_headers = rows_between_headers[1:]

        empty_row = None # Переменная пустой строки
        found_row = None # Переменная найденной строки, с которой нужно будет работать
        need_to_update = False # Флаг необходимости обновить контент
        # Перебираем строки, ищем только нужную. Попутно ищем - есть ли абсолютно пустая строка
        for row in rows_between_headers:
            cells = row.find_all('td')
            # Ищем абсолютную пустую строку
            if empty_row is None:
                all_cells_is_empty = True
                for c in cells:
                    text_content_is_empty = not c.get_text(strip=True)
                    tags_is_empty = all(str(tag).strip() == '<br/>' for tag in c.contents)
                    if not text_content_is_empty or not tags_is_empty:
                        all_cells_is_empty = False
                if all_cells_is_empty:
                    empty_row = row
                    continue

            # Ищем нужную строку. Для этого проверяем обязательные к заполнению поля
            for ins_name, insDict in cells_for_insert.items():
                if insDict.get("is_key", False) == True:
                    if insDict["value"] != cells[insDict["num_column"]].text.strip():
                        break
            # Если строка такая найдена, то добавляем ее в переменную и прерываем перебор строк
            else:
                found_row = row
                break

        # Работаем с найденной строкой, если такая есть
        if found_row:
            # Обновляем ячейки, если строка найдена
            cells = found_row.find_all('td')
            for ins_name, insDict in cells_for_insert.items():
                current_cell_original = cells[insDict["num_column"]]
                # Преобразовываем вытащенные данные в тип BeautifulSoup
                if not isinstance(current_cell_original, BeautifulSoup):
                    current_cell = BeautifulSoup(str(current_cell_original), 'html.parser')
                else:
                    current_cell = current_cell_original
                # Вытаскиваем контент из <td> (тега таблицы)
                if current_cell.td:
                    current_cell = current_cell.td.decode_contents()
                    # Прошлый код current_cell превращает в str, поэтому приходится еще раз преобразовывать
                    current_cell = BeautifulSoup(current_cell, 'html.parser')
                # Сравниваем и изменяем, при надобности
                if current_cell != insDict["value"] and str(current_cell) != insDict["value"]:
                    need_to_update = True
                    # Передаем на обновление
                    cells = self.update_cell_in_html_table(cells, insDict)

        # Иначе работаем с пустой строкой, если такая есть
        elif empty_row:
            need_to_update = True # Сразу помечаем, что страница требует обновления
            # Обновляем ячейки
            cells = empty_row.find_all('td')
            for ins_namje, insDict in cells_for_insert.items():
                # Передаем на обновление
                cells = self.update_cell_in_html_table(cells, insDict)

        # Иначе создаем новую строку и вставляем туда данные
        else:
            need_to_update = True # Сразу помечаем, что страница требует обновления
            new_row = soup.new_tag('tr')
            for i in range(num_cells_for_insert):
                new_row.append(soup.new_tag('td'))
            cells = new_row.find_all('td')
            for insName, insDict in cells_for_insert.items():
                # Передаем на обновление
                cells = self.update_cell_in_html_table(cells, insDict)
            # Вставляем строку перед следующим заголовком или в конец таблицы
            if next_header:
                # Вставляем перед заголовком
                next_header.find_previous('tr').insert_before(new_row) # Было в оригинале
            else:
                # Добавляем в конец, если других заголовков нет
                table_body.append(new_row)

        # Если мы прошлись по всем полям и пониманием, что значения не нуждаются в обновлении, то
        if not need_to_update:
            print("Нет необходимости обновлять Confluence - информация уже занесена")
            return


        # Получение обновленного HTML
        updated_html = str(soup)
        return updated_html


    def download_scan_csv(self):
        #MARK: download_scan_csv
        # from .libraries.harbor_tool import harbor_class
        # Блок работы с Harbor. Передаем ссылку на имэдж, вытаскиваем отчет о скане уязвимостей
        #try:
        #    harbor = harbor_class(package_harbor, confluence_login, confluence_password) # Логин и пароль от Harbor
        #    filepath_csv_with_reports_scan = harbor.export_csv_report()
        #except Exception as e:
        #    print(e)
        pass
        
        

    def main(self):
        #MARK: main
        self.get_environment_params()
        if not conf_upd.check_important_environments():
            return

        # Если есть sonar_flag, будем пытаться открыть sonar-project.properties
        # и построить на основе его баннеры
        if self.environments["SONAR_FLAG"]["value"]:
            # [![Статус порога качества](https://sonar.example.com/api/project_badges/measure?project=projectKey_example&metric=alert_status&token=HASH_LOGIN_PASS)]https://sonar.example.com/dashboard?id=projectKey_example)
            sonar_metrics_urls = []
            metrics = {
                "alert_status": "Статус порога качества"
                , "bugs": "Ошибки"
                }
            sonar_properties = self.read_sonar_properties()
            if sonar_properties:
                project_key, host_url, login = sonar_properties
                for eng_metr, ru_metr in metrics.items():
                    url_metric_markdown = f"{host_url}/api/project_badges/measure?project={project_key}&metric={eng_metr}&token={login}"
                    url_dashboard_markdown = f"{host_url}/dashboard?id={project_key}"
                    metric_html = f'<a href="{url_dashboard_markdown}"><img src="{url_metric_markdown}" alt="{ru_metr}"></a>'
                    sonar_metrics_urls.append(metric_html)

                sonar_metrics_urls_string = "".join(sonar_metrics_urls)
                sonar_html_content = BeautifulSoup(sonar_metrics_urls_string, 'html.parser')  # Парсим строку HTML в объект
                self.environments["SONAR_DATA"]["value"] = sonar_html_content
            else:
                self.environments["SONAR_FLAG"] = False
            # Подчищаем за собой
            del sonar_properties, project_key, host_url, login
            del url_metric_markdown \
                , url_dashboard_markdown \
                , metric_html \
                , sonar_metrics_urls \
                , sonar_metrics_urls_string \
                , sonar_html_content \
                , metrics
        else:
            del self.environments["SONAR_DATA"]
            del self.environments["SONAR_FLAG"]

        # Извлекаем Confluence объект и pageId распарсенный
        confluence, page_id = self.conluence_obj_and_pageId()
        # Вытаскиваем нужную страницу
        page = confluence.get_page_by_id(page_id=page_id, expand="body.storage")
        if not page:
            raise ValueError(f"Страница с ID {page_id} не найдена или недоступна.")
        # Извлечение текущего HTML-содержимого страницы
        page_content = page["body"]["storage"]["value"]
        # Модифицируем HTML контент
        updated_html = self.modify_html(page_content)

        # Если пришел изменный HTML, то
        if updated_html:
            try:
                # Обновление страницы с новым содержимым
                confluence.update_page(
                    page_id=page_id,
                    title=page['title'],
                    body=updated_html
                )
                print("Страница обновлена успешно!")

            except Exception as e:
                print(f"Ошибка при обновлении таблицы: {e}")





if __name__ == "__main__":
    #MARK: MAIN
    conf_upd = ConfluenceTableUpdater()
    conf_upd.main()