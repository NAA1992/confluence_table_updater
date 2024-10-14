import requests
import os
from urllib.parse import urlparse, parse_qs
import json
import base64
import time

class harbor_class():
    def __init__(self, raw_harbor_url, username, password):
        #MARK: __init__
        # Устанавливаем изначальные, главные переменные, от которых будем отталкиваться
        # domain2.domain1.com/projectName/repositoryName/apache-kafka:latest
        print("На вход поступил такой LINK HARBOR:", raw_harbor_url, "="*20, sep="\n")
        if not raw_harbor_url.startswith(('http://', 'https://')):
            raw_harbor_url = 'https://' + raw_harbor_url
            print(f"Добавили HTTPS к URL, теперь это: {raw_harbor_url}")
            
        # Парсим, вытаскиваем схему (http/https) и домен (domain.ru). Создаем шаблон API
        parsed_url = urlparse(raw_harbor_url)
        self.harbor_api_begin = f"{parsed_url.scheme}://{parsed_url.hostname}/api/v2.0"
        # Имя пользователя и пароль превращаем в токен, попутно конвертируя в байты (bytes) с кодировкой ascii, а затем кодируем в base64
        token = base64.b64encode(bytes("%s:%s" % (username,password), 'ascii'))
        # Формируем заголовок авторизации декодируя из ascii (секурность, все дела)
        auth_header = "Basic %s" % token.decode('ascii')
        self.headers = {'Authorization': auth_header}

        
        # Превращаем в список элементы после domain
        elements_path = parsed_url.path.strip("/").split("/")
        
        # Последний элемент - всегда Артефакт:тег
        # Вытаскиваем тег в отдельную переменную, артефакт оставляем внутри списка
        elements_path[-1], self.tag_artifact = elements_path[-1].split(":")

        # Имя репозитория через / . Для API слеш кодируем в %252F
        self.repository_fullname = "/".join(elements_path)
        self.repository_name = "/".join(elements_path[1:])
        self.repository_name_for_api = "%252F".join(elements_path[1:])
        
        # Имя проекта всегда идет первым
        self.project_name = elements_path[0]
        
        print(f"Распарсили значения. URL API: {self.harbor_api_begin}")
        print(f"Имя проекта: {self.project_name}")
        print(f"Имя репозитория: {self.repository_name}")
        print(f"Имя репозитория, участвующего в обращении к API: {self.repository_name_for_api}")
        print(f"Наименование тега у репозитория: {self.tag_artifact}")


        
    def check_auth(self):
        #MARK: check_auth
        try:
            response = self.make_request(url=f"{self.harbor_api_begin}/users/current")
            json_cont = response.json()
            return json_cont
        except Exception as e:
            raise Exception(f"Авторизация неуспешна: {e}")
        
        
    # Получение всех проектов
    def get_projects(self):
        #MARK: get_projects
        response = self.make_request(url=f"{self.harbor_api_begin}/projects")
        return response.json()
    
    
    # Получение всех проектов
    def get_repositories(self, project_name):
        #MARK: get_repositories
        response = self.make_request(url=f"{self.harbor_api_begin}/projects/{project_name}/repositories")
        return response.json()
    
    
    # Получение всех артефактов выбранного репозитория
    def get_artifacts(self, project_name, repository_name):
        #MARK: get_artifacts
        response = self.make_request(url=f"{self.harbor_api_begin}/projects/{project_name}/repositories/{repository_name}/artifacts")
        return response.json()
    
    
    # Получение информации об уязвимостях артефакта
    def get_reports_scan(self, project_name, repository_name, artifact_digest):
        #MARK: get_reports_scan
        response = self.make_request(url=f"{self.harbor_api_begin}/projects/{project_name}/repositories/{repository_name}/artifacts/{artifact_digest}", params={"with_scan_overview":True})
        return response.json()
    
    
    def get_cve_executions(self):
        #MARK: get_cve_executions
        response = self.make_request(url=f"{self.harbor_api_begin}/export/cve/executions")
        return response.json()
    
    
    def get_cve_execution_by_id(self, execution_id):
        #MARK: get_cve_execution_by_id
        response = self.make_request(url=f"{self.harbor_api_begin}/export/cve/execution/{execution_id}")
        return response.json()
    
    
    def post_cve_execution(self, project_id, repository_name, tag):
        #MARK: post_cve_execution
        headers = {"X-Scan-Data-Type": "application/vnd.security.vulnerability.report; version=1.1"
                   #, "X-Harbor-Csrf-Token": self.X_Harbor_Csrf_Token
                   , "Accept": "application/json"
                   , "Content-Type": "application/json"}
        data_dict = {
                "job_name": "python_export_cve",
                "projects": [
                    project_id
                ],
                "repositories": repository_name,
                # "cveIds": "string",
                "tags": tag
                }
        data = json.dumps(data_dict)
        response = self.make_request(url=f"{self.harbor_api_begin}/export/cve", method="POST", data=data, headers=headers)
        return response.json()
    
    
    def get_reports_log(self, project_name, repository_name, artifact_digest, report_id):
        response = self.make_request(url=f"{self.harbor_api_begin}/projects/{project_name}/repositories/{repository_name}/artifacts/{artifact_digest}/scan/{report_id}/log")
        return response.text
    

    def make_request(self, url, method = 'GET', **kwargs):
        #MARK: make_request
        kwargs.setdefault('headers', kwargs.get('headers', {}))
        # kwargs['headers']['Accept'] = 'application/json'
        kwargs['headers']['Authorization'] = self.headers['Authorization']
        if 'body' in kwargs:
            kwargs['headers']['Content-Type'] = 'application/json'
            kwargs['data'] = json.dumps(kwargs['body'])
            del kwargs['body']
        resp = requests.request(method, url, verify=True, **kwargs)  # если ошибка, то в json присутствует "errors"
        if resp.status_code >= 400:
            raise Exception("[Exception Message] - {}".format(resp.text))
        return resp

    def download_csv(self, execution_id, filename_csv):
        #MARK: download_csv
        headers = self.headers
        headers['Accept'] = 'text/csv'
        resp = requests.get(f"{self.harbor_api_begin}/export/cve/download/{execution_id}", headers=headers)
        resp.raise_for_status()
        # Сохраняем содержимое в файл
        with open(filename_csv, 'wb') as f:
            f.write(resp.content)
        print(f"Файл успешно скачан и сохранён: {filename_csv}")

    

    

    

    

    

    
    
    
    
    
       
        
    def export_csv_report(self):
        #MARK: export_csv_report
        # Авторизуемся
        print("Пробуем авторизоваться")
        auth_data = self.check_auth()
        print("Авторизация прошла успешно")
        
        # Получаем все проекты
        print("Получаем список проектов")
        projects = self.get_projects()
        print("Сверяем, есть ли заявленный проект, который был спарсен из URL")
        for project in projects:
            if project.get('name','') == self.project_name:
                print(f"Найден проект с названием {self.project_name}. Продолжаем работу")
                break
        else:
            raise Exception (f"Не найден проект с названием {self.project_name}")

        
        # Получаем все репозитории
        print("Получаем список репозиториев")
        repositories = self.get_repositories(project.get('name',''))
        print("Сверяем, есть ли заявленный репозиторий, который был спарсен из URL")
        for repository in repositories:
            if repository.get('name','') == self.repository_fullname:
                print(f"Найден репозиторий с названием {self.repository_fullname}. Продолжаем работу")
                break
        else:
            raise Exception (f"Не найден репозиторий с названием {self.repository_fullname}")
        
        # Получаем все артефакты
        print("Получаем список артефактов")     
        artifacts = self.get_artifacts(self.project_name, self.repository_name_for_api)
        print("Сверяем, есть ли заявленный тег артефакта, который был спарсен из URL")
        for artifact in artifacts:
            artifact_tags = artifact.get('tags', [])
            if isinstance(artifact_tags, list) and any(art_tag.get('name') == self.tag_artifact for art_tag in artifact_tags):
                print(f"Найден тег артефакта с названием {self.tag_artifact}. Продолжаем работу")
                break
        else:
            raise Exception (f"Не найден артефакт с названием {self.tag_artifact}")

        
        print("Проверяем, был ли раннее отсканирован артефакт на уязвимости")
        reports_scan = self.get_reports_scan(project['name'], self.repository_name_for_api, artifact['digest'])
        reports_scan_overview = reports_scan.get('scan_overview',{})
        reports_scan_overview['application/vnd.security.vulnerability.report; version=1.1']
        if 'application/vnd.security.vulnerability.report; version=1.1' in reports_scan_overview:
            current_level = reports_scan_overview['application/vnd.security.vulnerability.report; version=1.1']
            if current_level.get('scan_status', '').lower() == 'success':
                print(f"Скан на уязвимости обнаружен, он был выполнен {reports_scan_overview.get('end_time', 'unknown_date')}")
                # report_id = reports_scan_overview['report_id']
            else:
                raise Exception (f"Сканирование обнаружено, однако статус его отличается от Success. Текущий статус: {current_level.get('scan_status', '')}")
        else:
            raise Exception (f"Признаков сканирования на уязвимости на данном репозитории и артефакте не обнаружено. Выходим")
        
        # Получаем логи всех сканирований
        # report_log = self.get_reports_log(project['name'], self.repository_name_for_api, artifact['digest'], report_id)
        # Получаем все CSV Export исполнения
        # cve_exucutions = self.get_cve_executions()
        print("Отправляем формировать CSV выгрузку скана на уязвимости")
        forming_csv = self.post_cve_execution(project['project_id'], self.repository_name, self.tag_artifact)
        if 'errors' in forming_csv:
            print("Произошла ошибка при отправке команды на формирование CSV:")
            for err_key, err_val in forming_csv['errors']:
                print(f"{err_key}: {err_val}")
            raise Exception ("Выходим. Логи ошибок выше")
            
        id_forming_csv = forming_csv.get("id", "")
        time_sleep = 5
        print(f"Формирование CSV запущено, ID: {id_forming_csv}", f"Проверяем его готовность каждые секунд: {time_sleep}")
        cve_id_execution = {"file_present": False
                            , "status": "Running"}
        while cve_id_execution.get("status", "").lower() != "success":
            time.sleep(time_sleep)
            cve_id_execution = self.get_cve_execution_by_id(id_forming_csv)
            print(f"Текущий статус - {cve_id_execution.get('status', '')}")
        if not cve_id_execution.get("file_present", False):
            raise Exception ("Файл пуст. Скачивать нечего")
            
        print("Файл готов к скачиванию.")
        filename_csv = os.path.abspath(f"report_scan_{self.project_name}%252F%{self.repository_name_for_api}.csv")
        print(f"Скачиваем. Путь к файлу: {filename_csv}")
        self.download_csv(id_forming_csv, filename_csv)
        return filename_csv