# Confluence Table Updater

## Общее описание

Проект предназначен для обновления таблицы внутри страницы Confluence

Код заточен под парсинг таблицы следующего вида:

### Заголовок_1
| Имя пакета | Версия | Ссылка Nexus | Ссылка Harbor | SonarQube баннеры |
|------------|--------|--------------|---------------|-------------------|
| пакет_1    | 1.0    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |
| пакет_2    | 2.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |
| пакет_3    | 3.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |
### Заголовок_2
| Имя пакета | Версия | Ссылка Nexus | Ссылка Harbor | SonarQube баннеры |
|------------|--------|--------------|---------------|-------------------|
| пакет_1    | 1.0    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |
| пакет_2    | 2.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |
| пакет_3    | 3.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

текстом, эта же таблица

|Заголовок_1|

| Имя пакета | Версия | Ссылка Nexus | Ссылка Harbor | SonarQube баннеры |

| пакет_1    | 1.0    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

| пакет_2    | 2.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

| пакет_3    | 3.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

|Заголовок_2|

| Имя пакета | Версия | Ссылка Nexus | Ссылка Harbor | SonarQube баннеры |

| пакет_1    | 1.0    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

| пакет_2    | 2.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |

| пакет_3    | 3.1    | [URL_NEXUS](#)    | [URL_HARBOR](#)    | Banners           |


Порядок колонок может меняться, см. код

## Как использовать

Скрипт использует переменные окружения

Переменные Environment
- "CONFLUENCE_LOGIN": "LOGIN", - логин к confluence
- "CONFLUENCE_PASSWORD": "PASSWORD", - пароль к confluence
- "CONFLUENCE_URL": "https://conf.digitalms.ru/pages/viewpage.action?pageId=88429727", - страница Confluence
- "PACKAGE_HEADER": "Kafka", - То же, что и Заголовок_1, Заголовок_2
- "PACKAGE_NAME": "Пакет Python", - Имя пакета
- "PACKAGE_VERSION": "3.11.4", - Версия пакета
- "PACKAGE_NEXUS": "TEST Nexus_LINK", - URL к Nexus (необязательно, может отсутствовать)
- "PACKAGE_HARBOR": "Docker Harbor Link", - URL к Harbor
- "SONAR_FLAG": "" - Если пустое значение (или нет переменной) не будет добавлять SonarQube баннеры. Иначе будет пытаться обращаться к sonar-project.properties который лежит рядом со скриптом и на его основе будет строить баннеры

Обязательное содержимое sonar-project.properties:
- sonar.projectKey=projectKey_example - ключ проекта
- sonar.host.url=https://sonar.example.com - хост SonarQube
- sonar.login=HASH_LOGIN_PASS - логин hash

Внутри самого кода Python есть переменные, указывающие на номер колонки для каждого из значений. Нумерация начинается с 0.

Если у нас Имя проекта будет 3-м по счету, то переменная name_num_cell должна иметь 2

