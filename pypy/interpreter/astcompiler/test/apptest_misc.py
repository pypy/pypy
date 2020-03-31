def test_warning_to_error_translation():
    import warnings
    statement = """\
def wrong1():
    a = 1
    b = 2
    global a
    global b
"""
    with warnings.catch_warnings():
        warnings.filterwarnings("error", module="<test string>")
        try:
           compile(statement, '<test string>', 'exec')
        except SyntaxError as err:
           assert err.lineno is not None
           assert err.filename is not None
           assert err.offset is not None
           assert err.message is not None
