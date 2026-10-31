# depgraph

## 1. Общее описание

Консольный инструмент для визуализации графа зависимостей пакетов npm.
Зависимости читаются напрямую из реестра npm по HTTP, без менеджеров
пакетов и сторонних библиотек для получения данных.

Состояние проекта.

- [x] Этап 1. Минимальный прототип с конфигурацией
- [ ] Этап 2. Сбор данных
- [ ] Этап 3. Основные операции

Этапы 4 и 5 по согласованию с преподавателем не реализуются.

Вывод цветной (rich), поэтому вживую он выглядит ярче, чем в
транскриптах ниже. Транскрипты сняты с флагом `--no-color`.

## 2. Описание функций и настроек

### Запуск

```text
./run.sh [-c ФАЙЛ] [--no-color] [-h]
```

- `-c, --config ФАЙЛ` путь к TOML-конфигурации, по умолчанию `config.toml`.
- `--no-color` вывод без цветов и без рамок Unicode.
- Цвета также отключаются переменной `NO_COLOR` и выводом не в терминал.
- Коды выхода: 0 успех, 2 ошибка конфигурации, 130 прерывание.

### Формат конфигурации (TOML)

| Ключ | Тип | Обязателен | Смысл |
|------|-----|-----------|-------|
| `package` | строка | да | имя анализируемого пакета |
| `repository` | строка | да | URL реестра npm или путь к файлу тестового репозитория |
| `test_mode` | bool | нет, `false` | `true` включает режим тестового репозитория |
| `version` | строка | да | точная версия пакета, например `4.18.2` |
| `ascii_tree` | bool | нет, `true` | вывод зависимостей в виде ASCII-дерева |

Допущения.

- В обычном режиме `repository` это URL с `http` или `https`, имя пакета
  по правилам npm, версия точная (semver без диапазонов).
- В тестовом режиме `repository` это путь к существующему файлу, имя пакета
  состоит из больших латинских букв, версия не используется.
- Неизвестные ключи считаются ошибкой, это ловит опечатки.

### Модули

- `src/depgraph/config.py` загрузка и проверка конфигурации.
- `src/depgraph/render.py` оформление вывода через rich.
- `src/depgraph/cli.py` разбор аргументов и код выхода.
- `src/depgraph/errors.py` ожидаемые ошибки без трассировки.

## 3. Сборка, зависимости, тесты

```text
make install   установить зависимости (rich)
make test      запустить unittest
make run       запустить с config.toml
sh scripts/demo_errors.sh   показать обработку ошибок
```

Без make: `pip install -r requirements.txt`, затем
`PYTHONPATH=src python3 -m unittest discover -s tests`.

## 4. Примеры использования

Вывод параметров.

```text
$ ./run.sh --no-color -c examples/config_npm.toml
depgraph: граф зависимостей npm
Конфигурация: examples/config_npm.toml
                 Параметры                 
+-----------------------------------------+
| Ключ       | Значение                   |
|------------+----------------------------|
| package    | express                    |
| repository | https://registry.npmjs.org |
| test_mode  | false                      |
| version    | 4.18.2                     |
| ascii_tree | true                       |
+-----------------------------------------+
OK: конфигурация корректна
```

Справка.

```text
$ ./run.sh --help
usage: depgraph [-h] [-c ФАЙЛ] [--no-color]

Граф зависимостей пакета npm по TOML-конфигурации.

options:
  -h, --help            show this help message and exit
  -c ФАЙЛ, --config ФАЙЛ
                        путь к TOML-конфигурации (по умолчанию config.toml)
  --no-color            отключить цвета и рамки Unicode

Параметры задаются в TOML-файле: package, repository, test_mode, version,
ascii_tree. Пример: config.example.toml. Цвета отключаются флагом --no-color,
переменной NO_COLOR или выводом не в терминал.
```

Обработка ошибок для всех параметров.

```text
$ ./run.sh --no-color -c examples/errors/bad_package_name.toml
Ошибка конфигурации: некорректное имя npm-пакета: 'Express'
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/bad_test_mode.toml
Ошибка конфигурации: параметр test_mode должен быть true или false
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/bad_toml.toml
Ошибка конфигурации: некорректный TOML в examples/errors/bad_toml.toml: Invalid 
value (at end of document)
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/bad_url.toml
Ошибка конфигурации: repository должен быть URL вида https://registry.npmjs.org,
получено: 'ftp://example.com'
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/bad_version.toml
Ошибка конфигурации: версия '4.18' не похожа на точную semver-версию, например 
4.18.2
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/empty_package.toml
Ошибка конфигурации: параметр package не должен быть пустым
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/missing_package.toml
Ошибка конфигурации: не заданы обязательные параметры: package
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/test_bad_name.toml
Ошибка конфигурации: имя пакета 'app' не подходит для тестового режима, нужны 
большие латинские буквы, например A
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/test_repo_missing.toml
Ошибка конфигурации: файл тестового репозитория не найден: 
examples/repos/missing.txt
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/unknown_key.toml
Ошибка конфигурации: неизвестные параметры: color (допустимы: package, 
repository, version, test_mode, ascii_tree)
(код выхода 2)

$ ./run.sh --no-color -c examples/errors/no_such_file.toml
Ошибка конфигурации: файл не найден: examples/errors/no_such_file.toml
(код выхода 2)
```
