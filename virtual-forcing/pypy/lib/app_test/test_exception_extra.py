
def app_test_environmenterror_repr():
    import exceptions as ex 
    e = ex.EnvironmentError("hello")
    assert str(e) == "hello"
    e = ex.EnvironmentError(1, "hello")
    assert str(e) == "[Errno 1] hello"
    e = ex.EnvironmentError(1, "hello", "world")
    assert str(e) == "[Errno 1] hello: 'world'"

def app_test_import():
    import exceptions
    assert exceptions.SyntaxError is SyntaxError 

def app_test_baseexception():
    assert issubclass(Exception, BaseException)

def app_test_systemexit():
    assert issubclass(SystemExit, BaseException)

def app_test_keyboardinterrupt():
    assert issubclass(KeyboardInterrupt, BaseException)
