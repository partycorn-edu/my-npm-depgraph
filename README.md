# depgraph

## 1. Общее описание

Консольный инструмент для визуализации графа зависимостей пакетов npm.
Зависимости читаются напрямую из реестра npm по HTTP (urllib и json из
стандартной библиотеки), без менеджеров пакетов и сторонних библиотек для
получения данных. Для красивого вывода используется rich.

Программа строит полный граф с учётом транзитивных зависимостей, находит
циклы и печатает результат ASCII-деревом или таблицей. Есть режим
тестирования, где граф берётся из простого текстового файла с пакетами
`A`, `B`, `C` и так далее.

Состояние проекта.

- [x] Этап 1. Минимальный прототип с конфигурацией
- [x] Этап 2. Сбор данных
- [x] Этап 3. Основные операции

Этапы 4 и 5 по согласованию с преподавателем не реализуются.

Вывод цветной, поэтому вживую он выглядит ярче, чем в транскриптах ниже.
Транскрипты сняты с флагом `--no-color`.

## 2. Описание функций и настроек

### Запуск

```text
./run.sh [-c ФАЙЛ] [--no-color] [-h]
```

- `-c, --config ФАЙЛ` путь к TOML-конфигурации, по умолчанию `config.toml`.
- `--no-color` вывод без цветов и без рамок Unicode.
- Цвета также отключаются переменной `NO_COLOR` и выводом не в терминал.
- Коды выхода: 0 успех, 2 ошибка конфигурации, 3 ошибка репозитория,
  4 слишком глубокий граф,
  130 прерывание. Ожидаемые ошибки печатаются без трассировки.

### Формат конфигурации (TOML)

| Ключ | Тип | Обязателен | Смысл |
|------|-----|-----------|-------|
| `package` | строка | да | имя анализируемого пакета |
| `repository` | строка | да | URL реестра npm или путь к файлу тестового репозитория |
| `test_mode` | bool | нет, `false` | `true` включает режим тестового репозитория |
| `version` | строка | да | точная версия пакета, например `4.18.2` |
| `ascii_tree` | bool | нет, `true` | `true` дерево, `false` таблица пакет и его зависимости |

Допущения.

- В обычном режиме `repository` это URL с `http` или `https`, имя пакета
  по правилам npm, версия точная (semver без диапазонов).
- В тестовом режиме `repository` это путь к существующему файлу, имя пакета
  состоит из больших латинских букв, версия не используется (но поле
  обязательно, чтобы формат конфигурации не менялся).
- Относительные пути считаются от текущего каталога.
- Неизвестные ключи считаются ошибкой, это ловит опечатки.

### Режим тестового репозитория

Формат файла. Одна строка описывает один пакет.

```text
# комментарий
A: B C
B: C D
C:
```

- Слева имя пакета, справа его прямые зависимости через пробел или запятую.
- Имена состоят из больших латинских букв (`A`, `B`, `AB`).
- Пустые строки и строки с `#` пропускаются.
- Пакет описывается один раз. Пакет, упомянутый только как зависимость,
  считается листом, об этом выводится предупреждение.
- Корневой пакет из конфигурации должен быть описан в файле.

### Как строится граф

- Алгоритм BFS с рекурсией (`graph.py`). Функция обрабатывает один уровень
  графа и вызывает сама себя для следующего уровня. Каждый узел
  раскрывается ровно один раз.
- Циклы не приводят к зависанию, потому что уже встреченный узел не
  раскрывается повторно. Для отчёта запускается обход в глубину, который
  находит обратные рёбра. Цикл печатается как `A -> B -> C -> A`.
- В режиме npm узел это `имя@версия`. Диапазон из `dependencies`
  (`^1.2.3`, `~1.2`, `>=1 <2`, `1.x`, `*`, `||`, `a - b`) разрешается
  самописным разбором в `semver.py` в наибольшую стабильную версию, которая
  есть в реестре. Точные версии и dist-теги (`latest`) тоже поддержаны.
- Для одного пакета запрашивается один документ реестра, он кэшируется.

В дереве узел, который уже был показан выше и имеет зависимости, помечается
`(повтор, поддерево выше)` и не раскрывается заново. Ребро назад по текущему
пути помечается `(цикл)`.

Ограничения.

- Читаются только `dependencies`. Поля `devDependencies`, `peerDependencies`
  и `optionalDependencies` не учитываются.
- Не поддерживаются зависимости-алиасы (`npm:`), git и файловые URL,
  `workspace:`. Для них выводится понятная ошибка.
- Предрелизные версии выбираются только при точном указании.
- Результат зависит от состояния реестра на момент запуска.
- Глубина рекурсии ограничена лимитом Python (около 900 уровней графа), при превышении выводится ошибка и код 4.

### Сеть и прогресс

- Пока строится граф, в терминале показывается строка статуса с пакетом,
  данные которого запрашиваются сейчас, и числом обработанных пакетов.
  При выводе не в терминал статус не печатается.
- Если реестр недоступен с вашего адреса, укажите в `repository` зеркало,
  например `https://registry.npmmirror.com`, или задайте прокси переменной
  `HTTPS_PROXY`. Прокси из переменных окружения подхватывает `urllib`.

### Модули

- `src/depgraph/config.py` загрузка и проверка конфигурации.
- `src/depgraph/registry.py` клиент реестра npm на urllib и json.
- `src/depgraph/semver.py` разбор semver-диапазонов npm.
- `src/depgraph/sources.py` источники графа: npm и тестовый файл.
- `src/depgraph/graph.py` BFS с рекурсией и поиск циклов.
- `src/depgraph/tree.py` строки ASCII-дерева (логика без вывода).
- `src/depgraph/render.py` оформление вывода через rich.
- `src/depgraph/cli.py` разбор аргументов и код выхода.
- `src/depgraph/errors.py` ожидаемые ошибки.

## 3. Сборка, зависимости, тесты

```text
make install   установить зависимости (rich)
make test      запустить unittest
make run       запустить с config.toml
make demo      все демонстрации ниже
```

Без make: `pip install -r requirements.txt`, затем
`PYTHONPATH=src python3 -m unittest discover -s tests`.

Нужен Python 3.12 (используется `tomllib`). Тесты работают без сети, сеть
подменена заглушками и локальным HTTP-сервером.

## 4. Примеры использования

### Тестовый репозиторий

Все случаи ниже запускаются командой `sh scripts/demo_test_repo.sh`.

```text
$ cat examples/repos/basic.txt
# ромб: D нужен и B, и C
A: B C
B: D
C: D E
D: F
E:
F:
$ ./run.sh --no-color -c examples/test/basic.toml
depgraph: граф зависимостей A
A
|-- B
|   `-- D
|       `-- F
`-- C
    |-- D (повтор, поддерево выше)
    `-- E
OK: пакетов 6, связей 6
(код выхода 0)

$ cat examples/repos/cycle.txt
# цикл A -> B -> C -> A
A: B
B: C
C: A D
D:
$ ./run.sh --no-color -c examples/test/cycle.toml
depgraph: граф зависимостей A
A
`-- B
    `-- C
        |-- A (цикл)
        `-- D
Циклические зависимости: 1
  A -> B -> C -> A
OK: пакетов 4, связей 4
(код выхода 0)

$ cat examples/repos/cycle.txt
# цикл A -> B -> C -> A
A: B
B: C
C: A D
D:
$ ./run.sh --no-color -c examples/test/cycle_root_c.toml
depgraph: граф зависимостей C
C
|-- A
|   `-- B
|       `-- C (цикл)
`-- D
Циклические зависимости: 1
  C -> A -> B -> C
OK: пакетов 4, связей 4
(код выхода 0)

$ cat examples/repos/cycle.txt
# цикл A -> B -> C -> A
A: B
B: C
C: A D
D:
$ ./run.sh --no-color -c examples/test/cycle_table.toml
depgraph: граф зависимостей A
+--------------------+
| Пакет | Зависит от |
|-------+------------|
| A     | B          |
| B     | C          |
| C     | A, D       |
| D     | -          |
+--------------------+
Циклические зависимости: 1
  A -> B -> C -> A
OK: пакетов 4, связей 4
(код выхода 0)

$ cat examples/repos/deep.txt
A: B
B: C
C: D
D: E
E:
$ ./run.sh --no-color -c examples/test/deep.toml
depgraph: граф зависимостей A
A
`-- B
    `-- C
        `-- D
            `-- E
OK: пакетов 5, связей 4
(код выхода 0)

$ cat examples/repos/self_cycle.txt
# пакет зависит сам от себя
A: A B
B:
$ ./run.sh --no-color -c examples/test/self_cycle.toml
depgraph: граф зависимостей A
A
|-- A (цикл)
`-- B
Циклические зависимости: 1
  A -> A
OK: пакетов 2, связей 2
(код выхода 0)

$ cat examples/repos/single.txt
A:
$ ./run.sh --no-color -c examples/test/single.toml
depgraph: граф зависимостей A
A
OK: пакетов 1, связей 0
(код выхода 0)

$ cat examples/repos/two_cycles.txt
# два независимых цикла
A: B C
B: A
C: D
D: C
$ ./run.sh --no-color -c examples/test/two_cycles.toml
depgraph: граф зависимостей A
A
|-- B
|   `-- A (цикл)
`-- C
    `-- D
        `-- C (цикл)
Циклические зависимости: 2
  A -> B -> A
  C -> D -> C
OK: пакетов 4, связей 5
(код выхода 0)

$ cat examples/repos/undefined.txt
# пакет X упомянут, но не описан
A: B X
B:
$ ./run.sh --no-color -c examples/test/undefined.toml
depgraph: граф зависимостей A
A
|-- B
`-- X
Не описаны, считаются листьями: X
OK: пакетов 3, связей 2
(код выхода 0)
```

### Реальный реестр npm

```text
$ ./run.sh --no-color -c examples/npm/send_tree.toml
depgraph: граф зависимостей send@0.18.0
send@0.18.0
|-- debug@2.6.9
|   `-- ms@2.0.0
|-- depd@2.0.0
|-- destroy@1.2.0
|-- encodeurl@1.0.2
|-- escape-html@1.0.3
|-- etag@1.8.1
|-- fresh@0.5.2
|-- http-errors@2.0.0
|   |-- depd@2.0.0
|   |-- inherits@2.0.4
|   |-- setprototypeof@1.2.0
|   |-- statuses@2.0.1
|   `-- toidentifier@1.0.1
|-- mime@1.6.0
|-- ms@2.1.3
|-- on-finished@2.4.1
|   `-- ee-first@1.1.1
|-- range-parser@1.2.1
`-- statuses@2.0.1
OK: пакетов 19, связей 20
```

Та же работа в виде таблицы (`ascii_tree = false`).

```text
$ ./run.sh --no-color -c examples/npm/send_table.toml
depgraph: граф зависимостей send@0.18.0
+------------------------------------------------------------------------------+
| Пакет                | Зависит от                                            |
|----------------------+-------------------------------------------------------|
| send@0.18.0          | debug@2.6.9, depd@2.0.0, destroy@1.2.0,               |
|                      | encodeurl@1.0.2, escape-html@1.0.3, etag@1.8.1,       |
|                      | fresh@0.5.2, http-errors@2.0.0, mime@1.6.0, ms@2.1.3, |
|                      | on-finished@2.4.1, range-parser@1.2.1, statuses@2.0.1 |
| debug@2.6.9          | ms@2.0.0                                              |
| depd@2.0.0           | -                                                     |
| destroy@1.2.0        | -                                                     |
| encodeurl@1.0.2      | -                                                     |
| escape-html@1.0.3    | -                                                     |
| etag@1.8.1           | -                                                     |
| fresh@0.5.2          | -                                                     |
| http-errors@2.0.0    | depd@2.0.0, inherits@2.0.4, setprototypeof@1.2.0,     |
|                      | statuses@2.0.1, toidentifier@1.0.1                    |
| mime@1.6.0           | -                                                     |
| ms@2.1.3             | -                                                     |
| on-finished@2.4.1    | ee-first@1.1.1                                        |
| range-parser@1.2.1   | -                                                     |
| statuses@2.0.1       | -                                                     |
| ms@2.0.0             | -                                                     |
| inherits@2.0.4       | -                                                     |
| setprototypeof@1.2.0 | -                                                     |
| toidentifier@1.0.1   | -                                                     |
| ee-first@1.1.1       | -                                                     |
+------------------------------------------------------------------------------+
OK: пакетов 19, связей 20
```

Пакет со скоупом и пакет без зависимостей.

```text
$ ./run.sh --no-color -c examples/npm/scoped.toml
depgraph: граф зависимостей @babel/code-frame@7.22.13
@babel/code-frame@7.22.13
|-- @babel/highlight@7.25.9
|   |-- @babel/helper-validator-identifier@7.29.7
|   |-- chalk@2.4.2
|   |   |-- ansi-styles@3.2.1
|   |   |   `-- color-convert@1.9.3
|   |   |       `-- color-name@1.1.3
|   |   |-- escape-string-regexp@1.0.5
|   |   `-- supports-color@5.5.0
|   |       `-- has-flag@3.0.0
|   |-- js-tokens@4.0.0
|   `-- picocolors@1.1.1
`-- chalk@2.4.2 (повтор, поддерево выше)
OK: пакетов 12, связей 12
```

```text
$ ./run.sh --no-color -c examples/npm/no_deps.toml
depgraph: граф зависимостей ms@2.1.3
ms@2.1.3
OK: пакетов 1, связей 0
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

### Обработка ошибок

Ошибки конфигурации (`sh scripts/demo_errors.sh`).

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

Ошибки тестового репозитория (`sh scripts/demo_test_repo.sh examples/test_errors`).

```text
$ cat examples/repo_errors/bad_name.txt
A: B c
$ ./run.sh --no-color -c examples/test_errors/bad_name.toml
Ошибка репозитория: строка 1: имя 'c' должно состоять из больших латинских букв
(код выхода 3)

$ cat examples/repo_errors/duplicate.txt
A: B
A: C
$ ./run.sh --no-color -c examples/test_errors/duplicate.toml
Ошибка репозитория: строка 2: пакет 'A' описан дважды
(код выхода 3)

$ cat examples/repo_errors/empty.txt
# только комментарий

$ ./run.sh --no-color -c examples/test_errors/empty.toml
Ошибка репозитория: тестовый репозиторий не содержит описаний пакетов
(код выхода 3)

$ cat examples/repo_errors/no_colon.txt
A B C
$ ./run.sh --no-color -c examples/test_errors/no_colon.toml
Ошибка репозитория: строка 1: ожидался формат 'A: B C', получено 'A B C'
(код выхода 3)

$ cat examples/repos/basic.txt
# ромб: D нужен и B, и C
A: B C
B: D
C: D E
D: F
E:
F:
$ ./run.sh --no-color -c examples/test_errors/root_missing.toml
Ошибка репозитория: пакет 'Z' не описан в тестовом репозитории (описаны: A, B, 
C, D, E, F)
(код выхода 3)
```

Ошибки реестра (`sh scripts/demo_npm.sh examples/npm_errors`).

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
http://127.0.0.1:9/express. Проверьте сеть. Если реестр недоступен с вашего 
адреса, укажите в repository зеркало (например https://registry.npmmirror.com) 
или задайте прокси переменной HTTPS_PROXY.
(код выхода 3)
```
