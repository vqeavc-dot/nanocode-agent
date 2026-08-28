import pytest

from calculator import add, divide, multiply, subtract


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(7, 4) == 3


def test_multiply():
    assert multiply(3, 5) == 15


def test_divide():
    assert divide(6, 2) == 3


def test_divide_by_zero_raises_value_error():
    with pytest.raises(ValueError):
        divide(1, 0)

