from urllib.parse import urlparse
import requests
import json
import os
import pandas as pd
import csv

class DefectDojo:
    def __init__(self, str_url, token=None, username=None, password=None):
        url_parsed = urlparse(str_url)
        if not url_parsed.scheme:
            url_parsed._replace(scheme='https')
        if not url_parsed.hostname:
            raise Exception("Мы не смогли спарсить hostname из URL.")
        self.base_url = f"{url_parsed.scheme}://{url_parsed.hostname}"
        self.token = token
        self.username = username
        self.password = password
        self.headers = {'User-Agent': 'python-requests'
            , 'Content-Type': 'application/json'
            , 'Authorization': f'Token {self.token}'
            }

    def _authenticate(self):
        """
        Проверка авторизационных данных (токена). 
        Проверяет имеющийся токен, если его нет или ошибка - попытается получить токен через username & password
        """
        url_user_profile = f"{self.base_url}/api/v2/user_profile/"
        url_get_token = f"{self.base_url}/api/v2/api-token-auth/"
        headers = {
                    'Accept': 'application/json',
                    'Content-Type': 'application/x-www-form-urlencoded'
        }
        data = {
                'username': self.username,
                'password': self.password
        }
        if self.token:
            try:
                response = self.make_request(url=url_user_profile)
                return response.json()
            except:
                self.token = None
                del self.headers['Authorization']
        
        response = self.make_request(url=url_get_token, method='POST', headers=headers, data=data)
        self.token = response.json().get("token")
        self.headers['Authorization'] = f'Token {self.token}'
        
        return response.json()
        
    
    def make_request(self, url, method='GET', **kwargs):
        """
        Универсальная функция для запросов
        Если код >= 400, то ошибка, иначе - возвращает response
        """
        # Вместо кода ниже - работает верхний. Приоритет у kwargs['headers']
        headers = {**self.headers, **kwargs.pop('headers', {})} 
        #kwargs.setdefault('headers', kwargs.get('headers', {}))
        #for k, v in self.headers.items():
        #    if k not in kwargs['headers']:
        #        kwargs['headers'][k] = v
        # kwargs['headers']['Authorization'] = self.headers['Authorization']
        
        # Та же история. Оптимиация, кода поменьше
        if 'body' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('body'))
            #kwargs['data'] = json.dumps(kwargs['body'])
            #del kwargs['body']
        response = requests.request(method, url, headers=headers, verify=True, **kwargs)
        if response.status_code >= 400:
            raise Exception(f"[Exception Message] - {response.text}")
        return response
        
    def get_products(self, product_name=None):
        """
        Получение информации о продуктах(е) (их ID, имя, номера отчетов о сканировании)
        
        :product_name: Имя продукта. В Defect Dojo ищет по включению (не строгому равенству)
                        Если пусто, выдает список из всех продуктов
        :return: ответ JSON
        """
        url = f"{self.base_url}/api/v2/products/"
        params = {"name": product_name}
        response = self.make_request(url=url, params=params)
        return response.json()
        
    
    def get_product_scans(self, product_name):
        """
        Получение всего отчета о сканировании конкретного продукта
        
        :product_name: Имя продукта. Строго равенство.
        :return: ответ JSON
        """
        url = f"{self.base_url}/api/v2/findings/"
        params = {'product_name': product_name}
        response = self.make_request(url=url, params=params)
        return response.json()
        





if __name__ == '__main__':
    # Получаем значение из ENVIRONMENT (окружения). Если пустая строка, то None
    income_url = os.getenv('DOJO_URL') or None
    token = os.getenv("DOJO_TOKEN") or None
    username = os.getenv("DOJO_USERNAME") or None
    password = os.getenv("DOJO_PASSWORD") or None
    
    package_name = os.getenv("PACKAGE_NAME") or None
    
    dojo = DefectDojo(str_url=income_url, token=token, username=username, password=password)

    print("Пробуем авторизоваться...")
    dojo._authenticate()
    print("Авторизация успешна")
    
    print(f"Ищем есть ли продукт под именем '{package_name}'")
    product_found = False
    products_response = dojo.get_products(product_name=package_name)
    for product in products_response.get('results', []):
        if product.get('name') == package_name:
            product_found = True
            break
    if not product_found:
        raise Exception(f"Продукт {package_name} не найден")
    
    print("Ищем для данного продукта уязвимости")
    scans_product = dojo.get_product_scans(product_name=package_name)
    df_scan = pd.DataFrame(scans_product.get('results'), dtype=str)
    # df_scan = df_scan.map(lambda x: x.strip().replace("\n", " ") if isinstance(x, str) else x)
    #df_scan = df_scan.astype(str)
    for column, dtype in df_scan.dtypes.items():
        print(f"{column} - {dtype}")
    df_scan.to_csv('output.csv', index=False, quoting=csv.QUOTE_ALL, quotechar='"', sep=";")
    # df = pd.read_csv('output.csv', escapechar='\\')
    pass


