import sys
from pytest import raises
from types import TracebackType

def ve():
    raise ValueError

def get_tb():
    try:
        ve()
    except ValueError as e:
        return e.__traceback__

def test_mutation():
    tb = get_tb()

    # allowed
    tb.tb_next = None
    assert tb.tb_next is None

    tb2 = get_tb()
    tb.tb_next = tb2
    assert tb.tb_next is tb2

    with raises(TypeError):
        tb.tb_next = "rabc"

    # loops are forbidden
    with raises(ValueError):
        tb2.tb_next = tb

    with raises(ValueError):
        tb.tb_next = tb

    tb.tb_lasti = 1233
    assert tb.tb_lasti == 1233
    with raises(TypeError):
        tb.tb_lasti = "abc"

    tb.tb_lineno = 1233
    assert tb.tb_lineno == 1233
    with raises(TypeError):
        tb.tb_lineno = "abc"


def test_construct():
    frame = sys._getframe()
    tb = get_tb()
    tb2 = TracebackType(tb, frame, 1, 2)
    assert tb2.tb_next is tb
    assert tb2.tb_frame is frame
    assert tb2.tb_lasti == 1
    assert tb2.tb_lineno == 2

    tb2 = TracebackType(tb, frame, 1, -1)
    assert tb2.tb_next is tb
    assert tb2.tb_frame is frame
    assert tb2.tb_lasti == 1
    assert tb2.tb_lineno == -1

def test_can_subclass():
    with raises(TypeError):
        class TB(TracebackType):
            pass

class Buffer:
    def __init__(self):
        self.data = []

    def write(self, data):
        self.data.append(data)

    def flush(self):
        pass

    def get_lines(self):
        return "".join(self.data).splitlines()

def test_traceback_positions():
    def division_by_zero(a, b):
        return (
            a      + b / 0
        )

    with raises(ZeroDivisionError) as exc_info:
        division_by_zero(1, 2)

    original_std_err = sys.stderr
    sys.stderr = buffer = Buffer()
    original_exc_format = sys.excepthook(
        exc_info.type, exc_info.value, exc_info.value.__traceback__
    )
    sys.stderr = original_exc_format
    expected_exc_format = [
        '    a      + b / 0',
        '             ^^^^^',
        'ZeroDivisionError: division by zero'
    ]
    assert buffer.get_lines()[-3:] == expected_exc_format

def test_traceback_positions_on_cause():
    def foo(x):
        1 + 1/0 + 2

    def bar(x):
        try:
            1 + foo(x) + foo(x)
        except Exception as e:
            raise ValueError("oh no!") from e


    with raises(ValueError) as exc_info:
        bar(bar(bar(2)))

    original_std_err = sys.stderr
    sys.stderr = buffer = Buffer()
    original_exc_format = sys.excepthook(
        exc_info.type, exc_info.value, exc_info.value.__traceback__
    )
    sys.stderr = original_exc_format
    processed_lines = [
        line
        for line in buffer.get_lines()
        if __file__ not in line
    ]
    expected_exc_format = [
        'Traceback (most recent call last):',
        '    1 + foo(x) + foo(x)',
        '        ^^^^^^',
        '    1 + 1/0 + 2',
        '        ^^^',
        'ZeroDivisionError: division by zero',
        '',
        'The above exception was the direct cause of the following exception:',
        '',
        'Traceback (most recent call last):',
        '    bar(bar(bar(2)))',
        '            ^^^^^^',
        '    raise ValueError("oh no!") from e',
        'ValueError: oh no!'
    ]
    assert processed_lines == expected_exc_format
