# depgraph

## 1. Общее описание

Консольный инструмент для визуализации графа зависимостей пакетов npm.
Зависимости читаются напрямую из реестра npm по HTTP, без менеджеров
пакетов и сторонних библиотек для получения данных.

Состояние проекта.

- [x] Этап 1. Минимальный прототип с конфигурацией
- [x] Этап 2. Сбор данных
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
- Коды выхода: 0 успех, 2 ошибка конфигурации, 3 ошибка репозитория,
  130 прерывание.

### Формат конфигурации (TOML)

| Ключ | Тип | Обязателен | Смысл |
|------|-----|-----------|-------|
| `package` | строка | да | имя анализируемого пакета |
| `repository` | строка | да | URL реестра npm или путь к файлу тестового репозитория |
| `test_mode` | bool | нет, `false` | `true` включает режим тестового репозитория |
| `version` | строка | да | точная версия пакета, например `4.18.2` |
| `ascii_tree` | bool | нет, `true` | вывод зависимостей в виде ASCII-дерева |

Что делает программа на этапе 2.

- Запрашивает у реестра npm описание пакета (`GET <repository>/<package>`)
  и берёт поле `dependencies` указанной версии.
- Учитываются только обычные зависимости. Поля `devDependencies`,
  `peerDependencies` и `optionalDependencies` не читаются.
- При `ascii_tree = true` зависимости выводятся деревом, иначе таблицей.
- Вывод параметров из этапа 1 убран, как требует задание.
- Тестовый режим на этом этапе не работает, он появится на этапе 3.

Допущения.

- В обычном режиме `repository` это URL с `http` или `https`, имя пакета
  по правилам npm, версия точная (semver без диапазонов).
- В тестовом режиме `repository` это путь к существующему файлу, имя пакета
  состоит из больших латинских букв, версия не используется.
- Неизвестные ключи считаются ошибкой, это ловит опечатки.

### Модули

- `src/depgraph/config.py` загрузка и проверка конфигурации.
- `src/depgraph/registry.py` клиент реестра npm на urllib и json.
- `src/depgraph/render.py` оформление вывода через rich.
- `src/depgraph/cli.py` разбор аргументов и код выхода.
- `src/depgraph/errors.py` ожидаемые ошибки без трассировки.

## 3. Сборка, зависимости, тесты

```text
make install   установить зависимости (rich)
make test      запустить unittest
make run       запустить с config.toml
sh scripts/demo_errors.sh   ошибки конфигурации
sh scripts/demo_npm.sh      запросы к реальному реестру npm
sh scripts/demo_npm.sh examples/npm_errors   ошибки репозитория
```

Без make: `pip install -r requirements.txt`, затем
`PYTHONPATH=src python3 -m unittest discover -s tests`.

## 4. Примеры использования

Прямые зависимости в виде дерева.

```text
$ ./run.sh --no-color -c examples/npm/express_tree.toml
depgraph: прямые зависимости express@4.18.2
express@4.18.2
|-- accepts (~1.3.8)
|-- array-flatten (1.1.1)
|-- body-parser (1.20.1)
|-- content-disposition (0.5.4)
|-- content-type (~1.0.4)
|-- cookie (0.5.0)
|-- cookie-signature (1.0.6)
|-- debug (2.6.9)
|-- depd (2.0.0)
|-- encodeurl (~1.0.2)
|-- escape-html (~1.0.3)
|-- etag (~1.8.1)
|-- finalhandler (1.2.0)
|-- fresh (0.5.2)
|-- http-errors (2.0.0)
|-- merge-descriptors (1.0.1)
|-- methods (~1.1.2)
|-- on-finished (2.4.1)
|-- parseurl (~1.3.3)
|-- path-to-regexp (0.1.7)
|-- proxy-addr (~2.0.7)
|-- qs (6.11.0)
|-- range-parser (~1.2.1)
|-- safe-buffer (5.2.1)
|-- send (0.18.0)
|-- serve-static (1.15.0)
|-- setprototypeof (1.2.0)
|-- statuses (2.0.1)
|-- type-is (~1.6.18)
|-- utils-merge (1.0.1)
`-- vary (~1.1.2)
Всего прямых зависимостей: 31
```

То же таблицей (`ascii_tree = false`), пакет со скоупом и пакет без
зависимостей.

```text
$ ./run.sh --no-color -c examples/npm/scoped.toml
depgraph: прямые зависимости @babel/code-frame@7.22.13
@babel/code-frame@7.22.13
|-- @babel/highlight (^7.22.13)
`-- chalk (^2.4.2)
Всего прямых зависимостей: 2
```

```text
$ ./run.sh --no-color -c examples/npm/no_deps.toml
depgraph: прямые зависимости ms@2.1.3
У этой версии нет прямых зависимостей
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

Ошибки репозитория (нет пакета, нет версии, сеть недоступна).

```text
$ ./run.sh --no-color -c examples/npm_errors/missing_package.toml
Ошибка репозитория: пакет 'no-such-package-zzq9' не найден в 
https://registry.npmjs.org
(код выхода 3)

$ ./run.sh --no-color -c examples/npm_errors/missing_version.toml
Ошибка репозитория: версия 99.0.0 пакета 'express' не найдена, последние версии:
4.22.2, 4.22.3, 5.3.0
(код выхода 3)

$ ./run.sh --no-color -c examples/npm_errors/offline.toml
Ошибка репозитория: репозиторий недоступен ([Errno 111] Connection refused): 
http://127.0.0.1:9/express
(код выхода 3)
```
