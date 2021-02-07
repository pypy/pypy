import __pypy__
import sys
import io

def test_simple():
    oldstderr = sys.stderr
    sys.stderr = stringio = io.StringIO()
    try:
        try:
            raise ValueError
        except Exception as e:
            __pypy__.write_unraisable("testplace", e, None)
        output = stringio.getvalue()
        print(output)
        assert "testplace None" in output
        assert "Exception ignored in:" in output
        assert "ValueError" in output
    finally:
        sys.stderr = oldstderr

def test_custom_unraisablehook():
    l = []
    def ownhook(hookargs):
        l.append(hookargs)
    sys.unraisablehook = ownhook
    try:
        try:
            raise ValueError
        except Exception as e:
            obj = object()
            __pypy__.write_unraisable("testplace", e, obj)
            assert len(l) == 1
            args, = l
            assert args.exc_type is type(e)
            assert args.exc_value is e
            assert "testplace" in args.err_msg
            assert args.object is obj
    finally:
        sys.unraisablehook = sys.__unraisablehook__

def test_custom_unraisablehook_fails():
    def ownhook(hookargs):
        raise IndexError
    sys.unraisablehook = ownhook
    sys.stderr = stringio = io.StringIO()
    oldstderr = sys.stderr
    try:
        try:
            raise ValueError
        except Exception as e:
            obj = object()
            __pypy__.write_unraisable("testplace", e, obj)
        output = stringio.getvalue()
        print(output)
        assert "Exception ignored in sys.unraisablehook" in output
        assert "ownhook" in output
        assert "IndexError" in output
    finally:
        sys.unraisablehook = sys.__unraisablehook__
        sys.stderr = oldstderr
