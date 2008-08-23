import py.test

class AppTestRaise:
    def test_arg_as_string(self):
        def f():
            raise "test"

        import warnings
        warnings.simplefilter('error', DeprecationWarning)
        try:
            raises(DeprecationWarning, f)
        finally:
            warnings.simplefilter('default', DeprecationWarning)
        
    def test_control_flow(self):
        try:
            raise Exception
            raise AssertionError, "exception failed to raise"
        except:
            pass
        else:
            raise AssertionError, "exception executing else clause!"

    def test_1arg(self):
        try:
            raise SystemError, 1
        except Exception, e:
            assert e.args[0] == 1

    def test_2args(self):
        try:
            raise SystemError, (1, 2)
        except Exception, e:
            assert e.args[0] == 1
            assert e.args[1] == 2

    def test_instancearg(self):
        try:
            raise SystemError, SystemError(1, 2)
        except Exception, e:
            assert e.args[0] == 1
            assert e.args[1] == 2

    def test_more_precise_instancearg(self):
        try:
            raise Exception, SystemError(1, 2)
        except SystemError, e:
            assert e.args[0] == 1
            assert e.args[1] == 2

    def test_stringexc(self):
        a = "hello world"
        try:
            raise a
        except a, e:
            assert e == None
        try:
            raise a, "message"
        except a, e:
            assert e == "message"

    def test_builtin_exc(self):
        try:
            [][0]
        except IndexError, e:
            assert isinstance(e, IndexError)

    def test_raise_cls(self):
        def f():
            raise IndexError
        raises(IndexError, f)

    def test_raise_cls_catch(self):
        def f(r):
            try:
                raise r
            except LookupError:
                return 1
        raises(Exception, f, Exception)
        assert f(IndexError) == 1

    def test_raise_wrong(self):
        try:
            raise 1
        except TypeError:
            pass
        else:
            raise AssertionError, "shouldn't be able to raise 1"

    def test_raise_three_args(self):
        import sys
        try:
            raise ValueError
        except:
            exc_type,exc_val,exc_tb = sys.exc_info()
        try:
            raise exc_type,exc_val,exc_tb
        except:
            exc_type2,exc_val2,exc_tb2 = sys.exc_info()
        assert exc_type ==exc_type2
        assert exc_val ==exc_val2
        assert exc_tb ==exc_tb2

    def test_tuple_type(self):
        def f():
            raise ((StopIteration, 123), 456, 789)
        raises(StopIteration, f)

    def test_userclass(self):
        # PyPy classes are new-style so can't be raised

        class A:
            def __init__(self, x=None):
                self.x = x
        
        def f():
            try:
                raise A
            except A, a:
                assert a.x == None
        raises(TypeError, f)

        def f():
            try:
                raise A(42)
            except A, a:
                assert a.x == 42
        raises(TypeError, f)

    def test_it(self):
        C = _classobj('C', (), {})
        # this used to explode in the exception normalization step:
        try:
            {}[C]
        except KeyError:
            pass
