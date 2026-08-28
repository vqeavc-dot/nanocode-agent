from calculator import add, multiply, subtract


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(7, 4) == 3


def test_multiply():
    assert multiply(3, 5) == 15

