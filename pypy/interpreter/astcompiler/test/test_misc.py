from pypy.interpreter.astcompiler.misc import mangle

def test_mangle():
    assert mangle("foo", "Bar") == "foo"
    assert mangle("__foo__", "Bar") == "__foo__"
    assert mangle("foo.baz", "Bar") == "foo.baz"
    assert mangle("__", "Bar") == "__"
    assert mangle("___", "Bar") == "___"
    assert mangle("____", "Bar") == "____"
    assert mangle("__foo", "Bar") == "_Bar__foo"
    assert mangle("__foo", "_Bar") == "_Bar__foo"
    assert mangle("__foo", "__Bar") == "_Bar__foo"
    assert mangle("__foo", "___") == "__foo"
    assert mangle("___foo", "__Bar") == "_Bar___foo"

def app_test_warning_to_error_translation():
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("error", module="<test string>")
        statement = """\
def wrong1():
    a = 1
    b = 2
    global a
    global b
"""
        try:
           compile(statement, '<test string>', 'exec')
        except SyntaxError as err:
           assert err.lineno is not None
           assert err.filename is not None
           assert err.offset is not None
           assert err.msg is not None
