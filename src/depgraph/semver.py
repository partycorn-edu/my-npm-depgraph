"""Минимальная поддержка semver-диапазонов npm без внешних библиотек."""

import operator
import re

PARTIAL_RE = re.compile(
    r"^v?(\d+|[xX*])(?:\.(\d+|[xX*]))?(?:\.(\d+|[xX*]))?"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
STABLE_RE = re.compile(r"^\d+\.\d+\.\d+$")
OPERATOR_RE = re.compile(r"^(\^|~>?|>=|<=|>|<|=)?(.*)$")
SPACED_RE = re.compile(r"(>=|<=|>|<|=|\^|~>?)\s+")
HYPHEN_RE = re.compile(r"^\s*(\S+)\s+-\s+(\S+)\s*$")

WILDCARDS = ("x", "X", "*")
ZERO = (0, 0, 0)
MINOR = 1
PATCH = 2
COMPARE = {
    ">=": operator.ge,
    "<=": operator.le,
    ">": operator.gt,
    "<": operator.lt,
    "=": operator.eq,
}


def parse_partial(text):
    """Разобрать версию с возможными пропусками на [major, minor, patch]."""
    match = PARTIAL_RE.match(text)
    if not match:
        raise ValueError(f"не semver: '{text}'")
    parts = []
    wildcard = False
    for group in match.groups():
        wildcard = wildcard or group is None or group in WILDCARDS
        parts.append(None if wildcard else int(group))
    return parts


def fill(parts):
    """Заменить пропущенные части нулями."""
    return tuple(part or 0 for part in parts)


def next_up(parts):
    """Первая версия после всех версий, подходящих под частичную."""
    major, minor, _ = fill(parts)
    if parts[MINOR] is None:
        return (major + 1, 0, 0)
    return (major, minor + 1, 0)


def range_for(parts):
    """Диапазон для частичной версии вроде 1.2 или 1.x."""
    if parts[0] is None:
        return [(">=", ZERO)]
    return [(">=", fill(parts)), ("<", next_up(parts))]


def caret(parts):
    """Диапазон ^: допускает изменения справа от первой ненулевой части."""
    if parts[0] is None:
        return [(">=", ZERO)]
    major, minor, patch = fill(parts)
    if major or parts[MINOR] is None:
        upper = (major + 1, 0, 0)
    elif minor or parts[PATCH] is None:
        upper = (0, minor + 1, 0)
    else:
        upper = (0, 0, patch + 1)
    return [(">=", fill(parts)), ("<", upper)]


def tilde(parts):
    """Диапазон ~: допускает изменения патча, а без минора и минора."""
    return range_for(parts)


def at_most(parts):
    """Диапазон <=, для частичной версии включает всю её серию."""
    if parts[0] is None:
        return [(">=", ZERO)]
    if parts[PATCH] is None:
        return [("<", next_up(parts))]
    return [("<=", fill(parts))]


def greater(parts):
    """Диапазон >, для частичной версии начинается после всей серии."""
    if parts[0] is None:
        return [("<", ZERO)]
    if parts[PATCH] is None:
        return [(">=", next_up(parts))]
    return [(">", fill(parts))]


def exact(parts):
    """Точная версия или серия, если версия задана не полностью."""
    if parts[PATCH] is None:
        return range_for(parts)
    return [("=", fill(parts))]


def comparators(op, parts):
    """Превратить оператор и версию в список простых сравнений."""
    simple = {
        "^": caret,
        "~": tilde,
        "~>": tilde,
        "<=": at_most,
        ">": greater,
        "": exact,
        "=": exact,
    }
    if op in simple:
        return simple[op](parts)
    return [(op, fill(parts))]


def parse_token(token):
    """Разобрать один токен диапазона, например ^1.2.3 или >=2."""
    match = OPERATOR_RE.match(token)
    op, rest = match.group(1) or "", match.group(2)
    return comparators(op, parse_partial(rest))


def parse_hyphen(low, high):
    """Разобрать диапазон вида 1.2.3 - 2.3.4."""
    result = [(">=", fill(parse_partial(low)))]
    parts = parse_partial(high)
    if parts[0] is None:
        return result
    if parts[PATCH] is None:
        return result + [("<", next_up(parts))]
    return result + [("<=", fill(parts))]


def parse_set(text):
    """Разобрать набор сравнений, которые должны выполняться вместе."""
    hyphen = HYPHEN_RE.match(text)
    if hyphen:
        return parse_hyphen(hyphen.group(1), hyphen.group(2))
    found = []
    for token in SPACED_RE.sub(r"\1", text).split():
        found.extend(parse_token(token))
    return found or [(">=", ZERO)]


def parse_range(text):
    """Разобрать диапазон с альтернативами через ||."""
    return [parse_set(part) for part in text.split("||")]


def matches(version, alternatives):
    """Проверить версию-кортеж на соответствие хотя бы одной альтернативе."""
    return any(
        all(COMPARE[op](version, limit) for op, limit in comparator_set)
        for comparator_set in alternatives
    )


def max_satisfying(versions, spec):
    """Выбрать наибольшую стабильную версию под диапазон или None."""
    alternatives = parse_range(spec)
    best = None
    for text in versions:
        if not STABLE_RE.match(text):
            continue
        number = tuple(int(part) for part in text.split("."))
        if matches(number, alternatives) and (best is None or number > best[0]):
            best = (number, text)
    return best[1] if best else None
