import py, os, errno
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.error import decompose_valuefmt, get_operrcls2
from pypy.interpreter.error import wrap_oserror, new_exception_class


def test_decompose_valuefmt():
    assert (decompose_valuefmt("abc %s def") ==
            (("abc ", " def"), ('s',)))
    assert (decompose_valuefmt("%s%d%s") ==
            (("", "", "", ""), ('s', 'd', 's')))
    assert (decompose_valuefmt("%s%d%%%s") ==
            (("", "", "%", ""), ('s', 'd', 's')))

def test_get_operrcls2():
    cls, strings = get_operrcls2('abc %s def %d')
    assert strings == ("abc ", " def ", "")
    assert issubclass(cls, OperationError)
    inst = cls("w_type", strings, "hello", 42)
    assert inst._compute_value() == "abc hello def 42"
    cls2, strings2 = get_operrcls2('a %s b %d c')
    assert cls2 is cls     # caching
    assert strings2 == ("a ", " b ", " c")

def test_operationerrfmt():
    operr = operationerrfmt("w_type", "abc %s def %d", "foo", 42)
    assert isinstance(operr, OperationError)
    assert operr.w_type == "w_type"
    assert operr._w_value is None
    assert operr._compute_value() == "abc foo def 42"
    operr2 = operationerrfmt("w_type2", "a %s b %d c", "bar", 43)
    assert operr2.__class__ is operr.__class__
    operr3 = operationerrfmt("w_type2", "a %s b %s c", "bar", "4b")
    assert operr3.__class__ is not operr.__class__

def test_operationerrfmt_empty():
    py.test.raises(AssertionError, operationerrfmt, "w_type", "foobar")

def test_errorstr(space):
    operr = OperationError(space.w_ValueError, space.wrap("message"))
    assert operr.errorstr(space) == "ValueError: message"
    assert operr.errorstr(space, use_repr=True) == "ValueError: 'message'"

def test_wrap_oserror():
    class FakeSpace:
        w_OSError = [OSError]
        w_EnvironmentError = [EnvironmentError]
        def wrap(self, obj):
            return [obj]
        def call_function(self, exc, w_errno, w_msg, w_filename=None):
            return (exc, w_errno, w_msg, w_filename)
    space = FakeSpace()
    #
    e = wrap_oserror(space, OSError(errno.EBADF, "foobar"))
    assert isinstance(e, OperationError)
    assert e.w_type == [OSError]
    assert e.get_w_value(space) == ([OSError], [errno.EBADF],
                                    [os.strerror(errno.EBADF)], None)
    #
    e = wrap_oserror(space, OSError(errno.EBADF, "foobar"),
                     filename = "test.py",
                     exception_name = "w_EnvironmentError")
    assert isinstance(e, OperationError)
    assert e.w_type == [EnvironmentError]
    assert e.get_w_value(space) == ([EnvironmentError], [errno.EBADF],
                                    [os.strerror(errno.EBADF)],
                                    ["test.py"])
    #
    e = wrap_oserror(space, OSError(errno.EBADF, "foobar"),
                     filename = "test.py",
                     w_exception_class = [SystemError])
    assert isinstance(e, OperationError)
    assert e.w_type == [SystemError]
    assert e.get_w_value(space) == ([SystemError], [errno.EBADF],
                                    [os.strerror(errno.EBADF)],
                                    ["test.py"])

def test_new_exception(space):
    w_error = new_exception_class(space, '_socket.error')
    assert w_error.getname(space) == 'error'
    assert space.str_w(space.repr(w_error)) == "<class '_socket.error'>"
    operr = OperationError(w_error, space.wrap("message"))
    assert operr.match(space, w_error)
    assert operr.match(space, space.w_Exception)

    # subclass of ValueError
    w_error = new_exception_class(space, 'error', space.w_ValueError)
    operr = OperationError(w_error, space.wrap("message"))
    assert operr.match(space, w_error)
    assert operr.match(space, space.w_ValueError)

    # subclass of (ValueError, TypeError)
    w_bases = space.newtuple([space.w_ValueError, space.w_TypeError])
    w_error = new_exception_class(space, 'error', w_bases)
    operr = OperationError(w_error, space.wrap("message"))
    assert operr.match(space, w_error)
    assert operr.match(space, space.w_ValueError)
    assert operr.match(space, space.w_TypeError)

