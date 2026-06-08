from pytest import raises, skip

import sys

def test_generator():
    def f():
        yield 1
    assert next(f()) == 1

def test_generator2():
    def f():
        yield 1
    g = f()
    assert next(g) == 1
    with raises(StopIteration):
        next(g)

def test_attributes():
    def f():
        yield 1
        assert g.gi_running
    g = f()
    assert g.gi_code is f.__code__
    assert g.__name__ == 'f'
    assert g.gi_frame is not None
    assert not g.gi_running
    next(g)
    assert not g.gi_running
    with raises(StopIteration):
        next(g)
    assert not g.gi_running
    assert g.gi_frame is None
    assert g.gi_code is f.__code__
    assert g.__name__ == 'f'

def test_gi_suspended():
    def gisuspended():
        yield 1
        assert not g.gi_suspended
    g = gisuspended()
    assert not g.gi_suspended # not running yet
    next(g)
    assert g.gi_suspended
    with raises(StopIteration):
        next(g)
    assert not g.gi_suspended
    assert g.gi_frame is None

def test_generator3():
    def f():
        yield 1
    g = f()
    assert list(g) == [1]

def test_generator4():
    def f():
        yield 1
    g = f()
    assert [x for x in g] == [1]

def test_generator5():
    def f():
        v = (yield)
        yield v
    g = f()
    next(g)
    assert g.send(42) == 42

def test_throw1():
    def f():
        yield 2
    g = f()
    # two arguments version
    with raises(NameError):
        g.throw(NameError, "Error")

def test_throw2():
    def f():
        yield 2
    g = f()
    # single argument version
    with raises(NameError):
        g.throw(NameError("Error"))

def test_throw3():
    def f():
        try:
            yield 1
            yield 2
        except NameError:
            yield 3
    g = f()
    assert next(g) == 1
    assert g.throw(NameError("Error")) == 3
    with raises(StopIteration):
        next(g)

def test_throw4():
    def f():
        try:
            yield 1
            v = (yield 2)
        except NameError:
            yield 3
    g = f()
    assert next(g) == 1
    assert next(g) == 2
    assert g.throw(NameError("Error")) == 3
    with raises(StopIteration):
        next(g)

def test_throw5():
    def f():
        try:
            yield 1
        except Exception:
            x = 3
        try:
            yield x
        except Exception:
            pass
    g = f()
    next(g)
    # String exceptions are not allowed anymore
    with raises(TypeError):
        g.throw("Error")
    assert g.throw(Exception) == 3
    with raises(StopIteration):
        g.throw(Exception)

def test_throw6():
    def f():
        yield 2
    g = f()
    with raises(NameError):
        g.throw(NameError, "Error", None)


def test_throw_fail():
    def f():
        yield 1
    g = f()
    with raises(TypeError):
        g.throw(NameError("Error"), "error")

def test_throw_fail2():
    def f():
        yield 1
    g = f()
    with raises(TypeError):
        g.throw(list())

def test_throw_fail3():
    def f():
        yield 1
    g = f()
    with raises(TypeError):
        g.throw(NameError("Error"), None, "not tb object")

def test_throw_finishes_generator():
    def f():
        yield 1
    g = f()
    assert g.gi_frame is not None
    with raises(ValueError):
        g.throw(ValueError)
    assert g.gi_frame is None

def test_throw_bug():
    def f():
        try:
            x.throw(IndexError)     # => "generator already executing"
        except ValueError:
            yield 1
    x = f()
    res = list(x)
    assert res == [1]

def test_throw_on_finished_generator():
    def f():
        yield 1
    g = f()
    res = next(g)
    assert res == 1
    with raises(StopIteration):
        next(g)
    with raises(NameError):
        g.throw(NameError)

def test_throw_tb():
    def f():
        try:
            yield
        except ZeroDivisionError:
            raise
    g = f()
    try:
        1 / 0
    except ZeroDivisionError as v:
        try:
            g.throw(v)
        except Exception as w:
            tb = w.__traceback__
    levels = 0
    while tb:
        levels += 1
        tb = tb.tb_next
    assert levels == 3

def test_throw_context():
    # gen.throw(exc) must not modify exc.__context__
    def gen():
        try:
            yield
        except Exception:
            raise ValueError

    try:
        raise KeyError
    except KeyError:
        g = gen()
        next(g)
        exc1 = Exception(1)
        exc2 = Exception(2)
        exc2.__context__ = exc1
        try:
            g.throw(exc2)
        except ValueError:
            assert exc2.__context__ is exc1

def test_throw_bad_new_delivered_to_generator():
    # When E.__new__ returns the class itself instead of an instance,
    # the resulting TypeError should be delivered into the generator,
    # not raised directly to the throw() caller.
    class E(Exception):
        def __new__(cls, *args, **kwargs):
            return cls  # returns the class, not an instance

    # Case 1: generator does not catch TypeError -> TypeError propagates to caller
    def boring_generator():
        yield

    gen = boring_generator()
    with raises(TypeError, match='should have returned an instance of BaseException'):
        gen.throw(E)
    # After the throw, generator must be finished
    with raises(StopIteration):
        next(gen)

    # Case 2: generator catches TypeError at the yield point
    caught = []

    def catching_generator():
        try:
            yield
        except TypeError as exc:
            caught.append(str(exc))

    gen = catching_generator()
    next(gen)  # advance to the yield
    # throw E: TypeError from bad __new__ must be delivered into the generator;
    # the generator catches it, then finishes -> StopIteration
    with raises(StopIteration):
        gen.throw(E)
    assert len(caught) == 1
    assert 'should have returned an instance of BaseException' in caught[0]


def test_throw_invalid_args_do_not_kill_generator():
    # gen.throw(instance, bad_value) and gen.throw(type, val, bad_tb) should
    # raise TypeError to the caller but must NOT kill the generator.
    # This matches the CPython coroutine doctest scenario where after bad
    # throw args, the generator must still be usable.
    results = []

    def f():
        while True:
            try:
                results.append((yield))
            except ValueError as v:
                results.append('caught:%s' % str(v))

    g = f()
    next(g)  # advance to yield

    # throw with instance + separate value -> TypeError to caller, generator alive
    with raises(TypeError, match='instance exception may not have a separate value'):
        g.throw(ValueError(1), "bad")

    # generator must still be alive
    assert g.gi_frame is not None

    # generator must still catch exceptions thrown into it
    g.throw(ValueError("ok"))
    assert results == ['caught:ok']

    # throw with mismatched third arg -> TypeError, generator alive
    with raises(TypeError, match='throw\\(\\) third argument must be a traceback object'):
        g.throw(ValueError, "foo", 23)

    assert g.gi_frame is not None

    # now throw ValueError with traceback from sys.exc_info()
    try:
        raise ValueError
    except Exception:
        g.throw(*sys.exc_info())
    assert results == ['caught:ok', 'caught:']

    # generator must still be alive and accept sends
    g.send(42)
    assert results == ['caught:ok', 'caught:', 42]


def test_close():
    def f():
        yield 1
    g = f()
    assert g.close() is None

def test_close3():
    def f():
        try:
            yield 1
        except GeneratorExit:
            raise NameError
    g = f()
    next(g)
    with raises(NameError):
        g.close()

def test_close_fail():
    def f():
        try:
            yield 1
        except GeneratorExit:
            yield 2
    g = f()
    next(g)
    with raises(RuntimeError):
        g.close()

def test_close_on_collect():
    import gc
    def f():
        try:
            yield
        finally:
            f.x = 42
    g = f()
    next(g)
    del g
    gc.collect()
    assert f.x == 42

def test_generator_raises_typeerror():
    def f():
        yield 1
    g = f()
    with raises(TypeError):
        g.send()     # one argument required
    with raises(TypeError):
        g.send(1)  # not started, must send None

def test_generator_restart():
    def g():
        i = next(me)
        yield i
    me = g()
    with raises(ValueError):
        next(me)

def test_generator_expression():
    d = {}
    exec("res = sum(i*i for i in range(5))", d, d)
    assert d['res'] == 30

def test_generator_expression_2():
    def f():
        total = sum(i for i in [x for x in z])
        return total
    z = [1, 2, 7]
    assert f() == 10

def test_repr():
    def myFunc():
        yield 1
    g = myFunc()
    r = repr(g)
    assert r.startswith("<generator object test_repr.<locals>.myFunc at 0x")
    assert list(g) == [1]
    assert repr(g) == r

def test_unpackiterable_gen():
    g = (i * i for i in range(-5, 3))
    assert set(g) == set([0, 1, 4, 9, 16, 25])
    assert set(g) == set()
    assert set(i for i in range(0)) == set()

def test_exception_is_cleared_by_yield():
    def f():
        try:
            foobar
        except NameError:
            yield 5
            raise
    gen = f()
    next(gen)  # --> 5
    try:
        next(gen)
    except NameError:
        pass

def test_yield_return():
    def f():
        yield 1
        return 2
    g = f()
    assert next(g) == 1
    try:
        next(g)
    except StopIteration as e:
        assert e.value == 2
    else:
        assert False, 'Expected StopIteration'

def test_yield_from_basic():
    def f1():
        yield from []
        yield from [1, 2, 3]
        yield from f2()
    def f2():
        yield 4
        yield 5
    gen = f1()
    assert next(gen) == 1
    assert next(gen) == 2
    assert next(gen) == 3
    assert next(gen) == 4
    assert next(gen) == 5
    assert list(gen) == []

def test_yield_from_return():
    def f1():
        result = yield from f2()
        return result
    def f2():
        yield 1
        return 2
    g = f1()
    assert next(g) == 1
    try:
        next(g)
    except StopIteration as e:
        assert e.value == 2
    else:
        assert False, 'Expected StopIteration'

def test_yield_from_return_tuple():
    def f1():
        result = yield from f2()
        return result
    def f2():
        yield 1
        return (1, 2)
    g = f1()
    assert next(g) == 1
    try:
        next(g)
    except StopIteration as e:
        assert e.value == (1, 2)
    else:
        assert False, 'Expected StopIteration'

def test_set_name_qualname():
    class A:
        def f(self):
            yield 5
    g = A().f()
    assert g.__name__ == "f"
    assert g.__qualname__ == "test_set_name_qualname.<locals>.A.f"
    g.__name__ = "h.i"
    g.__qualname__ = "j.k"
    assert g.__name__ == "h.i"
    assert g.__qualname__ == "j.k"
    with raises(TypeError):
        g.__name__ = 42
    with raises(TypeError):
        g.__qualname__ = 42
    with raises((TypeError, AttributeError)):
        del g.__name__
    with raises((TypeError, AttributeError)):
        del g.__qualname__

def test_gi_yieldfrom():
    def g(x):
        assert gen.gi_yieldfrom is None
        yield x
        assert gen.gi_yieldfrom is None
    def f(x):
        assert gen.gi_yieldfrom is None
        yield from g(x)
        assert gen.gi_yieldfrom is None
        yield 42
        assert gen.gi_yieldfrom is None
    gen = f(5)
    assert gen.gi_yieldfrom is None
    assert next(gen) == 5
    assert gen.gi_yieldfrom.__name__ == 'g'
    assert next(gen) == 42
    assert gen.gi_yieldfrom is None

def test_gi_running_in_throw_generatorexit():
    # We must force gi_running to be True on the outer generators
    # when running an inner custom close() method.
    class A:
        def __iter__(self):
            return self
        def __next__(self):
            return 42
        def close(self):
            closed.append(gen.gi_running)
    def g():
        yield from A()
    gen = g()
    assert next(gen) == 42
    closed = []
    with raises(GeneratorExit):
        gen.throw(GeneratorExit)
    assert closed == [True]

def test_exc_info_in_generator():
    def g():
        try:
            raise ValueError
        except ValueError:
            yield sys.exc_info()[0]
            yield sys.exc_info()[0]
    try:
        raise IndexError
    except IndexError:
        gen = g()
        assert sys.exc_info()[0] is IndexError
        assert next(gen) is ValueError
        assert sys.exc_info()[0] is IndexError
        assert next(gen) is ValueError
        assert sys.exc_info()[0] is IndexError
        with raises(StopIteration):
            next(gen)
        assert sys.exc_info()[0] is IndexError

def test_exc_info_in_generator_2():
    import sys
    def g():
        yield sys.exc_info()[0]
        try:
            raise LookupError
        except LookupError:
            yield sys.exc_info()[0]
        yield sys.exc_info()[0]
    try:
        raise IndexError
    except IndexError:
        gen = g()     # the IndexError is not captured at all
    try:
        raise ValueError
    except ValueError:
        assert next(gen) is ValueError
        assert next(gen) is LookupError
        assert next(gen) is ValueError

def test_exc_info_in_generator_3():
    import sys
    def g():
        yield sys.exc_info()[0]
        yield sys.exc_info()[0]
        yield sys.exc_info()[0]
    gen = g()
    try:
        raise IndexError
    except IndexError:
        assert next(gen) is IndexError
    assert next(gen) is None
    try:
        raise ValueError
    except ValueError:
        assert next(gen) is ValueError

def test_exc_info_in_generator_4():
    import sys
    def g():
        assert sys.exc_info()[0] == IndexError
        try:
            raise ValueError
        except ValueError:
            assert sys.exc_info()[0] == ValueError
            yield 1
            assert sys.exc_info()[0] == ValueError
        assert sys.exc_info() == (None, None, None)
        yield 2
    gen = g()
    try:
        raise IndexError
    except IndexError:
        assert sys.exc_info()[0] == IndexError
        assert next(gen) == 1
        assert sys.exc_info()[0] == IndexError
    assert sys.exc_info() == (None, None, None)
    assert next(gen) == 2
    assert sys.exc_info() == (None, None, None)

def test_except_gen_except():
    def gen():
        try:
            assert sys.exc_info()[0] is None
            yield
            # we are called from "except ValueError:", TypeError must
            # inherit ValueError in its context
            raise TypeError()
        except TypeError as exc:
            assert sys.exc_info()[0] is TypeError
            assert type(exc.__context__) is ValueError
        # here we are still called from the "except ValueError:"
        assert sys.exc_info()[0] is ValueError
        yield
        assert sys.exc_info()[0] is None
        yield "done"

    g = gen()
    next(g)
    try:
        raise ValueError
    except Exception:
        next(g)

    assert next(g) == "done"
    assert sys.exc_info() == (None, None, None)

def test_multiple_invalid_sends():
    def mygen():
        yield 42
    g = mygen()
    with raises(TypeError):
        g.send(2)
    with raises(TypeError):
        g.send(2)

def test_delegating_close():
    """
    Test delegating 'close'
    """
    trace = []
    def g1():
        try:
            trace.append("Starting g1")
            yield "g1 ham"
            yield from g2()
            yield "g1 eggs"
        finally:
            trace.append("Finishing g1")
    def g2():
        try:
            trace.append("Starting g2")
            yield "g2 spam"
            yield "g2 more spam"
        finally:
            trace.append("Finishing g2")
    g = g1()
    for i in range(2):
        x = next(g)
        trace.append("Yielded %s" % (x,))
    g.close()
    assert trace == [
        "Starting g1",
        "Yielded g1 ham",
        "Starting g2",
        "Yielded g2 spam",
        "Finishing g2",
        "Finishing g1"
    ]

def test_handing_exception_while_delegating_close():
    """
    Test handling exception while delegating 'close'
    """
    trace = []
    def g1():
        try:
            trace.append("Starting g1")
            yield "g1 ham"
            yield from g2()
            yield "g1 eggs"
        finally:
            trace.append("Finishing g1")
    def g2():
        try:
            trace.append("Starting g2")
            yield "g2 spam"
            yield "g2 more spam"
        finally:
            trace.append("Finishing g2")
            raise ValueError("nybbles have exploded with delight")
    g = g1()
    for i in range(2):
        x = next(g)
        trace.append("Yielded %s" % (x,))
    with raises(ValueError) as excinfo:
        g.close()
    assert excinfo.value.args[0] == "nybbles have exploded with delight"
    assert isinstance(excinfo.value.__context__, GeneratorExit)
    assert trace == [
        "Starting g1",
        "Yielded g1 ham",
        "Starting g2",
        "Yielded g2 spam",
        "Finishing g2",
        "Finishing g1",
    ]

def test_delegating_throw():
    """
    Test delegating 'throw'
    """
    trace = []
    def g1():
        try:
            trace.append("Starting g1")
            yield "g1 ham"
            yield from g2()
            yield "g1 eggs"
        finally:
            trace.append("Finishing g1")
    def g2():
        try:
            trace.append("Starting g2")
            yield "g2 spam"
            yield "g2 more spam"
        finally:
            trace.append("Finishing g2")
    g = g1()
    for i in range(2):
        x = next(g)
        trace.append("Yielded %s" % (x,))
    e = ValueError("tomato ejected")
    with raises(ValueError) as excinfo:
        g.throw(e)
    assert excinfo.value.args[0] == "tomato ejected"
    assert trace == [
        "Starting g1",
        "Yielded g1 ham",
        "Starting g2",
        "Yielded g2 spam",
        "Finishing g2",
        "Finishing g1",
    ]

def test_delegating_throw_to_non_generator():
    """
    Test delegating 'throw' to non-generator
    """
    trace = []
    def g():
        try:
            trace.append("Starting g")
            yield from range(10)
        finally:
            trace.append("Finishing g")
    gi = g()
    for i in range(5):
        x = next(gi)
        trace.append("Yielded %s" % (x,))
    with raises(ValueError) as excinfo:
        gi.throw(ValueError("tomato ejected"))
    assert excinfo.value.args[0] == "tomato ejected"
    assert trace == [
        "Starting g",
        "Yielded 0",
        "Yielded 1",
        "Yielded 2",
        "Yielded 3",
        "Yielded 4",
        "Finishing g",
    ]

def test_broken_getattr_handling():
    """
    Test subiterator with a broken getattr implementation
    """
    import _io, sys
    class Broken:
        def __iter__(self):
            return self
        def __next__(self):
            return 1
        def __getattr__(self, attr):
            1 / 0

    def g():
        yield from Broken()

    gi = g()
    assert next(gi) == 1
    with raises(ZeroDivisionError):
        gi.send(1)

    gi = g()
    assert next(gi) == 1
    with raises(ZeroDivisionError):
        gi.throw(RuntimeError)

    gi = g()
    assert next(gi) == 1
    sys.stderr = _io.StringIO()
    unraisables = []
    def ownhook(hookargs):
        unraisables.append(hookargs)
    oldhook = sys.unraisablehook
    sys.unraisablehook = ownhook
    try:
        gi.close()
    finally:
        sys.unraisablehook = oldhook
    assert len(unraisables) == 1
    assert isinstance(unraisables[0].exc_value,  ZeroDivisionError)

def test_returning_value_from_delegated_throw():
    """
    Test returning value from delegated 'throw'
    """
    trace = []
    class LunchError(Exception):
        pass
    def g1():
        try:
            trace.append("Starting g1")
            yield "g1 ham"
            yield from g2()
            yield "g1 eggs"
        finally:
            trace.append("Finishing g1")
    def g2():
        try:
            trace.append("Starting g2")
            yield "g2 spam"
            yield "g2 more spam"
        except LunchError:
            trace.append("Caught LunchError in g2")
            yield "g2 lunch saved"
            yield "g2 yet more spam"
    g = g1()
    for i in range(2):
        x = next(g)
        trace.append("Yielded %s" % (x,))
    e = LunchError("tomato ejected")
    g.throw(e)
    for x in g:
        trace.append("Yielded %s" % (x,))
    assert trace == [
        "Starting g1",
        "Yielded g1 ham",
        "Starting g2",
        "Yielded g2 spam",
        "Caught LunchError in g2",
        "Yielded g2 yet more spam",
        "Yielded g1 eggs",
        "Finishing g1",
    ]

def test_catching_exception_from_subgen_and_returning():
    """
    Test catching an exception thrown into a
    subgenerator and returning a value
    """
    trace = []
    def inner():
        try:
            yield 1
        except ValueError:
            trace.append("inner caught ValueError")
        return 2

    def outer():
        v = yield from inner()
        trace.append("inner returned %r to outer" % v)
        yield v
    g = outer()
    trace.append(next(g))
    trace.append(g.throw(ValueError))
    assert trace == [
        1,
        "inner caught ValueError",
        "inner returned 2 to outer",
        2,
    ]

def test_exception_context():
    import operator
    def f():
        try:
            raise ValueError
        except ValueError:
            yield from map(operator.truediv, [2, 3], [4, 0])
    gen = f()
    assert next(gen) == 0.5
    with raises(ZeroDivisionError) as excinfo:
        next(gen)
    assert isinstance(excinfo.value.__context__, ValueError)


def test_stopiteration_turned_into_runtime_error():
    def badgenerator(x):
        if x == 5:
            raise StopIteration
        yield x
    with raises(RuntimeError):
        next(badgenerator(5))

def test_stopiteration_can_be_caught():
    def g():
        raise StopIteration
    def finegenerator(x):
        yield x
        if x == 5:
            try:
                g()
            except StopIteration:
                pass
        yield x
    gen = finegenerator(5)
    next(gen) # fine
    next(gen) # fine

def test_generator_stop_cause():
    def gen1():
        yield 42
    my_gen = gen1()
    assert next(my_gen) == 42
    stop_exc = StopIteration('spam')
    with raises(RuntimeError) as e:
        my_gen.throw(StopIteration, stop_exc, None)
    assert e.value.__cause__ is stop_exc
    assert e.value.__context__ is stop_exc

def test_return_tuple():
    def gen1():
        return (yield 1)
    gen = gen1()
    assert next(gen) == 1
    with raises(StopIteration) as excinfo:
        gen.send((2,))
    assert excinfo.value.value == (2,)

def test_return_stopiteration():
    def gen1():
        return (yield 1)
    gen = gen1()
    assert next(gen) == 1
    with raises(StopIteration) as excinfo:
        gen.send(StopIteration(2))
    assert isinstance(excinfo.value, StopIteration)
    assert excinfo.value.value.value == 2

def test_list_building_wrong_exception():
    def gen1():
        raise ValueError
        yield 2
    with raises(ValueError):
        [*gen1()]

    def gen1():
        raise ValueError
        yield from [1, 2, 3]
    with raises(ValueError):
        [*gen1()]

def test_throw_context_set_from_active_exception():
    # When throw() is called on a generator suspended inside an except block,
    # the thrown exception's __context__ must be set to the active exception.
    def f():
        try:
            raise KeyError('a')
        except Exception:
            yield

    gen = f()
    gen.send(None)
    with raises(ValueError) as cm:
        gen.throw(ValueError)
    context = cm.value.__context__
    assert type(context) is KeyError
    assert context.args == ('a',)

def test_throw_context_set_inside_generator():
    # Same as above but the context is also visible from inside the generator.
    results = []
    def f():
        try:
            raise KeyError('a')
        except Exception:
            try:
                yield
            except Exception as exc:
                results.append((type(exc.__context__), exc.__context__.args))
                yield 'done'

    gen = f()
    gen.send(None)
    val = gen.throw(ValueError)
    assert val == 'done'
    assert results == [(KeyError, ('a',))]

def test_throw_non_exception_error_message():
    # gen.throw() with a non-exception should report
    # "classes or instances deriving from BaseException".
    def f():
        yield
    g = f()
    with raises(TypeError) as cm:
        g.throw("abc")
    assert "classes or instances deriving from BaseException" in str(cm.value)
    assert "str" in str(cm.value)

    g2 = f()
    with raises(TypeError) as cm2:
        g2.throw(list)
    assert "classes or instances deriving from BaseException" in str(cm2.value)

def test_throw_bad_new_returns_non_instance():
    # If E.__new__ returns the class itself instead of an instance,
    # throw() should say "should have returned an instance of BaseException".
    class E(Exception):
        def __new__(cls, *args, **kwargs):
            return cls

    def f():
        yield

    g = f()
    with raises(TypeError) as cm:
        g.throw(E)
    assert "should have returned an instance of BaseException" in str(cm.value)

def test_throw_bad_new_closes_generator():
    # After throw() raises TypeError due to __new__ returning a non-instance,
    # the generator must be exhausted (next() raises StopIteration).
    class E(Exception):
        def __new__(cls, *args, **kwargs):
            return cls

    def f():
        yield

    g = f()
    with raises(TypeError):
        g.throw(E)
    with raises(StopIteration):
        next(g)

def test_generatorexit_unraisable_has_traceback():
    # When a generator is GC'd while suspended and its close() raises
    # RuntimeError("generator ignored GeneratorExit"), the unraisable exception
    # must carry a non-None traceback.
    import gc

    def f():
        try:
            yield
        except GeneratorExit:
            yield "ignored!"

    unraisables = []
    import sys
    old_hook = sys.unraisablehook
    def hook(info):
        unraisables.append(info)
    sys.unraisablehook = hook
    try:
        g = f()
        next(g)
        del g
        gc.collect()
    finally:
        sys.unraisablehook = old_hook

    assert len(unraisables) == 1
    info = unraisables[0]
    assert info.exc_type is RuntimeError
    assert "generator ignored GeneratorExit" in str(info.exc_value)
    assert info.exc_traceback is not None
