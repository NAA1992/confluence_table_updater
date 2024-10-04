from atlassian import Confluence
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import os
import sys
import requests

# https://conf.digitalms.ru/pages/viewpage.action?pageId=36867901



if __name__ == "__main__":
    #MARK: MAIN
    
    # ПОЛНОСТЬЮ копирует контент из одной страницы в другую (заменяет)

    # Получение значений из переменных окружения
    confluence_login = os.getenv('CONFLUENCE_LOGIN', '')
    confluence_password = os.getenv('CONFLUENCE_PASSWORD', '')

    confluence_url = os.getenv('CONFLUENCE_URL', '')

    # Разбираем URL на компоненты
    parsed_url = urlparse(confluence_url)
    # Извлекаем домен
    domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
    # Извлекаем параметр pageId
    query_params = parse_qs(parsed_url.query)
    page_id = query_params.get('pageId', [None])[0]
    
    NUM_PAGE_TARGET = 88429727 # Куда будем копировать контент из источника ПОЛНОСТЬЮ

    

    try:
        # Подключение к Confluence
        confluence = Confluence(
            url=domain,
            username=confluence_login,
            password=confluence_password  # Можно использовать API-токен вместо пароля
        )

        # Получение содержимого страницы
        page_source = confluence.get_page_by_id(36867901, expand='body.storage')
        
        # Извлечение текущего HTML-содержимого страницы
        page_source_content = page_source['body']['storage']['value']

    except requests.exceptions.ConnectionError:
        print("Не удалось подключиться к URL Confluence. Проверьте URL или интернет-соединение.")
        sys.exit(1)
    except Exception as e:
        print(f"Ошибка при подключении к Confluence: {e}")
        sys.exit(1)
        


    try:
        # Парсим HTML с помощью BeautifulSoup
        soup = BeautifulSoup(page_source_content, 'html.parser')

    except ValueError as ve:
        print(f"Ошибка при обработке страницы: {ve}")
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка при парсинге HTML: {e}")
        sys.exit(1)



    # Получение обновленного HTML
    updated_html = str(soup)

    page_target = confluence.get_page_by_id(NUM_PAGE_TARGET, expand='body.storage')
    # Обновление страницы с новым содержимым
    confluence.update_page(
        page_id=NUM_PAGE_TARGET,
        title=page_target['title'],
        body=updated_html
    )

    print("Страница обновлена успешно!")