import pytest
from esm.support.util_text import *


def run_test_cases(func, test_cases):
    for text, expected, error in test_cases:
        if error:
            with pytest.raises(error):
                func(text)
        else:
            assert func(text) == expected


def test_str_to_be_evaluated():

    texts_list = [
        # expressions to be processed
        ("[a]", True, None),
        ("['a']", True, None),
        ('["a"]', True, None),
        ("{'a': 1, 'b': ['ciao']}", True, None),
        # strings not to be processed
        ('a', False, None),
        ('a, [1, 2]', False, None),
        ('a, b', False, None),
        # other types not allowed
        (2, None, TypeError),
        ([1, 2, 3], None, TypeError),
        # strings not well formatted (brackets not correctly open/closed)
        ('(a, b', None, ValueError),
        ('a, b]', None, ValueError),
        ("{'a': 1, 'b': ['ciao'}", None, ValueError),
        ("{'a': 1, 'b': ['ciao', (1,]}", None, ValueError),
    ]

    run_test_cases(str_to_be_evaluated, texts_list)


def test_add_brackets():

    texts_list = [
        # non allowed types
        (True, None, TypeError),
        (2, None, TypeError),
        (['a', 'b'], None, TypeError),
        # str not representing iterables (no actions)
        ('hello', 'hello', None),
        ("hello", 'hello', None),
        # str representing iterables with brackets (no actions)
        ('(a, b)', '(a, b)', None),
        ('[a, b]', '[a, b]', None),
        ('{a: b}', '{a: b}', None),
        # str representing list without brackets
        ('a, b', '[a, b]', None),
        ("a, [b, c]", "[a, [b, c]]", None),
        # str representing dict without brackets
        ('a: b', '{a: b}', None),
        ('a: b, c: {d: [e, f]}', '{a: b, c: {d: [e, f]}}', None),
        ('a, {b: [c, d]}', '[a, {b: [c, d]}]', None),
        # str not well formatted (brackets not correctly open/closed)
        ('(a, b', None, ValueError),
        ('a, b]', None, ValueError),
        ('{a: 1, b: [ciao}', None, ValueError),
        ('{a: 1, b: [ciao, (1,]}', None, ValueError),
    ]

    run_test_cases(add_brackets, texts_list)


def test_add_quotes():

    texts_list = [
        # non allowed types
        ([1, 2, 3], None, TypeError),
        # strings representing values to be quoted
        ("a", "'a'", None),
        ("[a]", "['a']", None),
        ("[a, b]", "['a', 'b']", None),
        ("[a,b]", "['a', 'b']", None),
        ("{a: b}", "{'a': 'b'}", None),
        ("a: b, c: {d: [e]}", "'a': 'b', 'c': {'d': ['e']}", None),
        ("{a: b, c: {d: [e]}}", "{'a': 'b', 'c': {'d': ['e']}}", None),
        # strings including numbers:
        ("[a, 1, 4.3]", "['a', 1, 4.3]", None),
    ]

    run_test_cases(add_quotes, texts_list)


def test_evaluate_bool():

    texts_list = [
        (True, True, None),
        ('True', True, None),
        ('FALSE', False, None),
        (['a', 'True'], ['a', True], None),
        ({'a': ['b', 'True']}, {'a': ['b', True]}, None),
    ]

    run_test_cases(evaluate_bool, texts_list)


def test_process_str():

    texts_list = [
        # Any type different than str
        (True, True, None),
        ([1, 2], [1, 2], None),
        # generic str not representing bool | iterable (no actions)
        ('a', 'a', None),
        ('a @ b + c', 'a @ b + c', None),
        # str representing iterables (processed)
        ('a, b', ['a', 'b'], None),
        ('[a, b]', ['a', 'b'], None),
        ('a: [b, c, d]', {'a': ['b', 'c', 'd']}, None),
        ('a: b', {'a': 'b'}, None),
        ('a: b, c: {d: [e, f]}', {'a': 'b', 'c': {'d': ['e', 'f']}}, None),
        # str representing bool in util_text bool_map variable
        ('True', True, None),
        ('FALSE', False, None),
        ('a, True', ['a', True], None),
        ('a: True, c: {d: [True]}', {'a': True, 'c': {'d': [True]}}, None),
        # case of keys as numbers
        ('1: a, 2: b', {1: 'a', 2: 'b'}, None),
    ]

    run_test_cases(process_str, texts_list)
