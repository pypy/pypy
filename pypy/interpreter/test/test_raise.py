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

    def test_revert_exc_info_2_finally(self):
        import sys
        assert sys.exc_info() == (None, None, None)
        try:
            try:
                raise ValueError
            finally:
                try:
                    try:
                        raise IndexError
                    finally:
                        assert sys.exc_info()[0] is IndexError
                except IndexError:
                    pass
                assert sys.exc_info()[0] is ValueError
        except ValueError:
            pass
        assert sys.exc_info() == (None, None, None)

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

    def test_userclass_catch(self):
        # classes can't be caught unless they inherit from BaseException
        class A(object):
            pass

        for exc in A, (ZeroDivisionError, A):
            try:
                try:
                    1 / 0
                except exc:
                    pass
            except TypeError:
                pass
            else:
                fail('Expected TypeError')

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
        """
        # this test checks bug-to-bug cpython compatibility
        e = ValueError()
        e.__bases__ = (5,)
        try:
            raise e
        except ValueError:
            pass

        # explodes on CPython and py.test, not sure why

        flag = False
        class metaclass(type):
            def __getattribute__(self, name):
                if flag and name == '__bases__':
                    fail("someone read bases attr")
                else:
                    return type.__getattribute__(self, name)
        class A(BaseException, metaclass=metaclass):
            pass
        try:
            a = A()
            flag = True
            raise a
        except A:
            pass
        """

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

    def test_clear_last_exception_on_break(self):
        import sys
        for i in [0]:
            try:
                raise ValueError
            except ValueError:
                break
        assert sys.exc_info() == (None, None, None)

class AppTestRaiseContext:

    def test_instance_context(self):
        context = IndexError()
        try:
            try:
                raise context
            except:
                raise OSError()
        except OSError as e:
            assert e.__context__ is context
        else:
            fail('No exception raised')

    def test_class_context(self):
        context = IndexError
        try:
            try:
                raise context
            except:
                raise OSError()
        except OSError as e:
            assert e.__context__ != context
            assert isinstance(e.__context__, context)
        else:
            fail('No exception raised')

    def test_internal_exception(self):
        try:
            try:
                1/0
            except:
                xyzzy
        except NameError as e:
            assert isinstance(e.__context__, ZeroDivisionError)
        else:
            fail("No exception raised")

    def test_cycle_broken(self):
        try:
            try:
                1/0
            except ZeroDivisionError as e:
                raise e
        except ZeroDivisionError as e:
            assert e.__context__ is None
        else:
            fail("No exception raised")

    def test_reraise_cycle_broken(self):
        try:
            try:
                xyzzy
            except NameError as a:
                try:
                    1/0
                except ZeroDivisionError:
                    raise a
        except NameError as e:
            assert e.__context__.__context__ is None
        else:
            fail("No exception raised")

    def test_context_once_removed(self):
        context = IndexError()
        def func1():
            func2()
        def func2():
            try:
                1/0
            except ZeroDivisionError as e:
                assert e.__context__ is context
            else:
                fail('No exception raised')
        try:
            raise context
        except:
            func1()

    def test_frame_spanning_cycle_broken(self):
        context = IndexError()
        def func():
            try:
                1/0
            except Exception as e1:
                try:
                    raise context
                except Exception as e2:
                    assert e2.__context__ is e1
                    assert e1.__context__ is None
            else:
                fail('No exception raised')
        try:
            raise context
        except:
            func()

    def testCauseSyntax(self):
        """
        try:
            try:
                try:
                    raise TypeError
                except Exception:
                    raise ValueError from None
            except ValueError as exc:
                assert exc.__cause__ is None
                assert exc.__suppress_context__ is True
                assert isinstance(exc.__context__, TypeError)
                exc.__suppress_context__ = False
                raise exc
        except ValueError as exc:
            e = exc
        assert e.__cause__ is None
        assert e.__suppress_context__ is False
        assert isinstance(e.__context__, TypeError)
        """

    def test_context_in_builtin(self):
        context = IndexError()
        try:
            try:
                raise context
            except:
                compile('pass', 'foo', 'doh')
        except ValueError as e:
            assert e.__context__ is context
        else:
            fail('No exception raised')

    def test_context_with_suppressed(self):
        class RaiseExc:
            def __init__(self, exc):
                self.exc = exc
            def __enter__(self):
                return self
            def __exit__(self, *exc_details):
                raise self.exc

        class SuppressExc:
            def __enter__(self):
                return self
            def __exit__(self, *exc_details):
                return True

        try:
            with RaiseExc(IndexError):
                with SuppressExc():
                    with RaiseExc(ValueError):
                        1/0
        except IndexError as exc:
            assert exc.__context__ is None
        else:
            assert False, "should have raised"

    def test_with_exception_context(self):
        class Ctx:
            def __enter__(self):
                pass
            def __exit__(self, *e):
                1/0
        try:
            with Ctx():
                raise ValueError
        except ZeroDivisionError as e:
            assert e.__context__ is not None
            assert isinstance(e.__context__, ValueError)
        else:
            assert False, "should have raised"


class AppTestTraceback:

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

    def test_sets_traceback(self):
        import types
        try:
            raise IndexError()
        except IndexError as e:
            assert isinstance(e.__traceback__, types.TracebackType)
        else:
            fail("No exception raised")

    def test_accepts_traceback(self):
        import sys
        def get_tb():
            try:
                raise OSError()
            except:
                return sys.exc_info()[2]
        tb = get_tb()
        try:
            raise IndexError().with_traceback(tb)
        except IndexError as e:
            assert e.__traceback__ != tb
            assert e.__traceback__.tb_next is tb
        else:
            fail("No exception raised")

    def test_invalid_reraise(self):
        try:
            raise
        except RuntimeError as e:
            assert "No active exception" in str(e)
        else:
            fail("Expected RuntimeError")

    def test_invalid_cause(self):
        """
        try:
            raise IndexError from 5
        except TypeError as e:
            assert "exception cause" in str(e)
        else:
            fail("Expected TypeError")
            """

    def test_invalid_cause_setter(self):
        """
        class Setter(BaseException):
            def set_cause(self, cause):
                self.cause = cause
            __cause__ = property(fset=set_cause)
        try:
            raise Setter from 5
        except TypeError as e:
            assert "exception cause" in str(e)
        else:
            fail("Expected TypeError")
            """
