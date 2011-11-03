import py.test

class AppTestRaise:
    def test_arg_as_string(self):
        def f():
            raise "test"
        raises(TypeError, f)

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

    def test_reraise(self):
        # some collection of funny code
        import sys
        raises(ValueError, """
            import sys
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    assert sys.exc_info()[0] is ValueError
                    raise
        """)
        raises(ValueError, """
            def foo():
                import sys
                assert sys.exc_info()[0] is ValueError
                raise
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    foo()
        """)
        raises(IndexError, """
            def spam():
                import sys
                try:
                    raise KeyError
                except KeyError:
                    pass
                assert sys._getframe().f_exc_type is ValueError
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    spam()
        """)

        try:
            raise ValueError
        except:
            try:
                raise KeyError
            except:
                ok = sys.exc_info()[0] is KeyError
        assert ok

        raises(IndexError, """
            import sys
            try:
                raise ValueError
            except:
                some_traceback = sys.exc_info()[2]
            try:
                raise KeyError
            except:
                try:
                    raise IndexError, IndexError(), some_traceback
                finally:
                    assert sys.exc_info()[0] is KeyError
                    assert sys.exc_info()[2] is not some_traceback
        """)

    def test_tuple_type(self):
        def f():
            raise ((StopIteration, 123), 456, 789)
        raises(StopIteration, f)

    def test_userclass(self):
        # new-style classes can't be raised unless they inherit from
        # BaseException

        class A(object):
            def __init__(self, x=None):
                self.x = x
        
        def f():
            raise A
        raises(TypeError, f)

        def f():
            raise A(42)
        raises(TypeError, f)

    def test_it(self):
        class C:
            pass
        # this used to explode in the exception normalization step:
        try:
            {}[C]
        except KeyError:
            pass

    def test_oldstyle_userclass(self):
        class A:
            def __init__(self, val=None):
                self.val = val
        class Sub(A):
            pass

        try:
            raise Sub
        except IndexError:
            assert 0
        except A, a:
            assert a.__class__ is Sub

        sub = Sub()
        try:
            raise sub
        except IndexError:
            assert 0
        except A, a:
            assert a is sub

        try:
            raise A, sub
        except IndexError:
            assert 0
        except A, a:
            assert a is sub
            assert sub.val is None

        try:
            raise Sub, 42
        except IndexError:
            assert 0
        except A, a:
            assert a.__class__ is Sub
            assert a.val == 42

        try:
            {}[5]
        except A, a:
            assert 0
        except KeyError:
            pass

    def test_catch_tuple(self):
        class A:
            pass
        
        try:
            raise ValueError
        except (ValueError, A):
            pass
        else:
            fail("Did not raise")

        try:
            raise A()
        except (ValueError, A):
            pass
        else:
            fail("Did not raise")

    def test_obscure_bases(self):
        # this test checks bug-to-bug cpython compatibility
        e = ValueError()
        e.__bases__ = (5,)
        try:
            raise e
        except ValueError:
            pass

        # explodes on CPython and py.test, not sure why

        flag = False
        class A(BaseException):
            class __metaclass__(type):
                def __getattribute__(self, name):
                    if flag and name == '__bases__':
                        fail("someone read bases attr")
                    else:
                        return type.__getattribute__(self, name)

        try:
            a = A()
            flag = True
            raise a
        except 42:
            pass
        except A:
            pass

    def test_new_returns_bad_instance(self):
        class MyException(Exception):
            def __new__(cls, *args):
                return object()
        raises(TypeError, "raise MyException")
