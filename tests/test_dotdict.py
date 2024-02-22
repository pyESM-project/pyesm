import pytest
from src.support.dotdict import DotDict


def test_dot_access():
    d = DotDict({'a': 1, 'b': 2})
    assert d.a == 1
    assert d.b == 2


def test_bracket_access():
    d = DotDict({'a': 1, 'b': 2})
    assert d['a'] == 1
    assert d['b'] == 2


def test_attribute_assignment():
    d = DotDict()
    d.c = 3
    assert d.c == 3


def test_bracket_assignment():
    d = DotDict()
    d['c'] = 3
    assert d['c'] == 3


def test_nonexistent_attribute_access():
    d = DotDict()
    with pytest.raises(AttributeError):
        _ = d.foo


def test_nonexistent_key_access():
    d = DotDict()
    with pytest.raises(KeyError):
        _ = d['foo']
