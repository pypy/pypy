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
        '             ~~^~~',
        'ZeroDivisionError: division by zero'
    ]
    assert buffer.get_lines()[-3:] == expected_exc_format

def test_traceback_positions_trailing_whitespace():
    # issue gh-5219
    def name_error():
            # note this has excess trailing whitespace
            a = b          

    with raises(NameError) as exc_info:
        name_error()

    original_std_err = sys.stderr
    sys.stderr = buffer = Buffer()
    original_exc_format = sys.excepthook(
        exc_info.type, exc_info.value, exc_info.value.__traceback__
    )
    sys.stderr = original_exc_format
    expected_exc_format = [
        '    a = b',
        '        ^',
        "NameError: name 'b' is not defined"
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
        '        ~^~',
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

def test_colors_in_traceback():
    import os
    def division_by_zero(a, b):
        return (
            a      + b / 0 # abc
        )

    old_value = os.environ.get('FORCE_COLOR', None)
    os.environ['FORCE_COLOR'] = '1'
    try:
        from _colorize import can_colorize, ANSIColors
        assert can_colorize()
        with raises(ZeroDivisionError) as exc_info:
            division_by_zero(1, 2)

        original_std_err = sys.stderr
        sys.stderr = buffer = Buffer()
        original_exc_format = sys.excepthook(
            exc_info.type, exc_info.value, exc_info.value.__traceback__
        )
        sys.stderr = original_std_err
        expected_exc_format = [
            f'    a      + {ANSIColors.BOLD_RED}b / 0{ANSIColors.RESET} # abc',
            f'             {ANSIColors.BOLD_RED}~~^~~{ANSIColors.RESET}',
            f'{ANSIColors.BOLD_MAGENTA}ZeroDivisionError{ANSIColors.RESET}: {ANSIColors.MAGENTA}division by zero{ANSIColors.RESET}'
        ]
        assert buffer.get_lines()[-3:] == expected_exc_format

    finally:
        if old_value is None:
            del os.environ['FORCE_COLOR']
        else:
            os.environ['FORCE_COLOR'] = old_value

def test_old_format_works():
    """test that overriding traceback.TracebackException with a class
    that doesn't know about colorize (like exceptiongroup._formatting) still works
    issue 5004
    """
    import traceback
    
    def division_by_zero(a, b):
        return (
            a      + b / 0 # abc
        )
    
    class MyTracebackException(traceback.TracebackException):

        def format(self, *, chain=None):
            return "done"

    traceback_exception_original_format = traceback.TracebackException.format
    traceback.TracebackException.format = MyTracebackException.format
    original_std_err = sys.stderr
    sys.stderr = buffer = Buffer()
    try:
        with raises(ZeroDivisionError) as exc_info:
            division_by_zero(1, 2)

        lines = traceback.format_exception(exc_info.type, exc_info.value, exc_info.value.__traceback__)
        print("".join(lines), file=sys.stderr)
        expected_exc_format = ["done"]
        assert buffer.get_lines() == expected_exc_format
    finally:
        sys.stderr = original_std_err
        traceback.TracebackException.format = traceback_exception_original_format

