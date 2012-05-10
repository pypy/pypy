import py.test

class AppTestRaise:
    def test_arg_as_string(self):
        def f():
            raise "test"
        raises(TypeError, f)

    def test_control_flow(self):
        try:
            raise Exception
            raise AssertionError("exception failed to raise")
        except:
            pass
        else:
            raise AssertionError("exception executing else clause!")

    def test_store_exception(self):
        try:
            raise ValueError
        except Exception as e:
            assert e


    def test_args(self):
        try:
            raise SystemError(1, 2)
        except Exception as e:
            assert e.args[0] == 1
            assert e.args[1] == 2

    def test_builtin_exc(self):
        try:
            [][0]
        except IndexError as e:
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
            raise AssertionError("shouldn't be able to raise 1")

    def test_revert_exc_info_1(self):
        import sys
        assert sys.exc_info() == (None, None, None)
        try:
            raise ValueError
        except:
            pass
        assert sys.exc_info() == (None, None, None)

    def test_revert_exc_info_2(self):
        import sys
        assert sys.exc_info() == (None, None, None)
        try:
            raise ValueError
        except:
            try:
                raise IndexError
            except:
                assert sys.exc_info()[0] is IndexError
            assert sys.exc_info()[0] is ValueError
        assert sys.exc_info() == (None, None, None)

    def test_raise_with___traceback__(self):
        import sys
        try:
            raise ValueError
        except:
            exc_type,exc_val,exc_tb = sys.exc_info()
        try:
            exc_val.__traceback__ = exc_tb
            raise exc_val
        except:
            exc_type2,exc_val2,exc_tb2 = sys.exc_info()
        assert exc_type is exc_type2
        assert exc_val is exc_val2
        assert exc_tb is exc_tb2.tb_next

    def test_reraise_1(self):
        raises(IndexError, """
            import sys
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    assert sys.exc_info()[0] is IndexError
                    raise
        """)

    def test_reraise_2(self):
        raises(IndexError, """
            def foo():
                import sys
                assert sys.exc_info()[0] is IndexError
                raise
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    foo()
        """)

    def test_reraise_3(self):
        raises(IndexError, """
            def spam():
                import sys
                try:
                    raise KeyError
                except KeyError:
                    pass
                assert sys.exc_info()[0] is IndexError
            try:
                raise ValueError
            except:
                try:
                    raise IndexError
                finally:
                    spam()
        """)

    def test_reraise_4(self):
        import sys
        try:
            raise ValueError
        except:
            try:
                raise KeyError
            except:
                ok = sys.exc_info()[0] is KeyError
        assert ok

    def test_reraise_5(self):
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
                    raise IndexError().with_traceback(some_traceback)
                finally:
                    assert sys.exc_info()[0] is IndexError
                    assert sys.exc_info()[2].tb_next is some_traceback
        """)

    def test_nested_reraise(self):
        raises(TypeError, """
            def nested_reraise():
                raise
            try:
                raise TypeError("foo")
            except:
                nested_reraise()
        """)

    def test_with_reraise_1(self):
        class Context:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_value, exc_tb):
                return True

        def fn():
            try:
                raise ValueError("foo")
            except:
                with Context():
                    pass
                raise
        raises(ValueError, "fn()")


    def test_with_reraise_2(self):
        class Context:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_value, exc_tb):
                return True

        def fn():
            try:
                raise ValueError("foo")
            except:
                with Context():
                    raise KeyError("caught")
                raise
        raises(ValueError, "fn()")

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

    def test_catch_tuple(self):
        class A(Exception):
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
        except A:
            pass

    def test_new_returns_bad_instance(self):
        class MyException(Exception):
            def __new__(cls, *args):
                return object()
        raises(TypeError, "raise MyException")


    def test_pop_exception_value(self):
        # assert that this code don't crash
        for i in range(10):
            try:
                raise ValueError
            except ValueError as e:
                continue
