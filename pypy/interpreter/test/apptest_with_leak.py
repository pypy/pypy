"""Isolate the nested try/except+reraise sys.exc_info leak."""
import sys


def _clear():
    # Force sys.exc_info to None before each test since apptest runs may have
    # leaked state from pypy's own startup.
    try:
        raise Exception
    except Exception:
        pass
    # Now sys.exc_info should be None if POP_EXCEPT works. If this itself
    # leaks, the simplest case leaks.


def test_0_simplest_clear():
    _clear()
    # If the basic try/except/pass does not restore, EVERYTHING leaks.
    assert sys.exc_info() == (None, None, None), sys.exc_info()


def test_E_nested_bare_except():
    _clear()
    try:
        try:
            raise ImportError("original")
        except ImportError:
            raise ValueError("new")
    except ValueError:
        pass
    assert sys.exc_info() == (None, None, None), sys.exc_info()


def test_F_nested_as_name():
    _clear()
    try:
        try:
            raise ImportError("original")
        except ImportError as e:
            raise ValueError(str(e))
    except ValueError:
        pass
    assert sys.exc_info() == (None, None, None), sys.exc_info()


def test_G_flat_try_except_pass():
    _clear()
    try:
        raise ImportError("single")
    except ImportError:
        pass
    assert sys.exc_info() == (None, None, None), sys.exc_info()


def test_inner_with_exit_raises_suppressed_by_outer():
    # Inner CM's __exit__ raises; try/except doesn't match;
    # outer CM's __exit__ suppresses. Nothing should escape.
    class InnerCM:
        def __enter__(self): return None
        def __exit__(self, *args):
            raise OSError("Cannot close")

    class OuterCM:
        def __init__(self): self.exited_with = None
        def __enter__(self): return None
        def __exit__(self, *args):
            self.exited_with = args[0]
            return True  # suppress

    outer = OuterCM()
    with outer:
        try:
            with InnerCM():
                raise AttributeError("body error")
        except IsADirectoryError:
            pass
    assert outer.exited_with is OSError, outer.exited_with


def test_shutil_pattern():
    # Reproduce the shutil.copyfile failure.
    # Multiple early returns inside the inner with cause duplicate_exits_without_lineno
    # to copy the with-exit code, which confuses the linear exception table scan and
    # leaves the fallback path (copyfileobj) with no exception table coverage.
    # Structure mirrors shutil.copyfile:
    #   outer with (suppresses) -> try/except -> inner with (raises in __exit__)
    #     -> fast paths with early returns -> fallback that raises via None return
    class InnerCM:
        def __enter__(self):
            return None  # intentional -- fallback body raises AttributeError
        def __exit__(self, exc_type, exc_val, exc_tb):
            if exc_type is not None:
                raise OSError("dest close failed")
            return False

    class OuterCM:
        exited_with = 'not called'
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            self.exited_with = exc_type
            return True  # suppress everything

    class GiveupOnFastCopy(Exception):
        pass

    def copyfile(use_fast1, use_fast2):
        result = []
        outer = OuterCM()
        with outer:
            try:
                with InnerCM() as f:
                    if use_fast1:
                        try:
                            result.append('fast1')
                            return result
                        except GiveupOnFastCopy:
                            pass
                    elif use_fast2:
                        try:
                            result.append('fast2')
                            return result
                        except GiveupOnFastCopy:
                            pass
                    # fallback: f is None, raises AttributeError
                    result.append(f.read)
            except IsADirectoryError:
                pass
        return outer

    import dis
    dis.dis(copyfile)

    # Fast paths exit normally -- outer/inner __exit__(None,None,None) not raising.
    assert copyfile(True, False) == ['fast1']
    assert copyfile(False, True) == ['fast2']

    # Fallback path: f.read raises AttributeError, inner __exit__ raises OSError,
    # outer __exit__ should suppress OSError and copyfile returns outer.
    outer_result = copyfile(False, False)
    assert isinstance(outer_result, OuterCM), outer_result
    assert outer_result.exited_with is OSError, repr(outer_result.exited_with)
