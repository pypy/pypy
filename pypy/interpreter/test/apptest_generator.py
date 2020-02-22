from pytest import raises, skip

def test_generator():
    def f():
        yield 1
    assert f().next() == 1

def test_generator2():
    def f():
        yield 1
    g = f()
    assert g.next() == 1
    with raises(StopIteration):
        g.next()

def test_attributes():
    def f():
        yield 1
        assert g.gi_running
    g = f()
    assert g.gi_code is f.__code__
    assert g.__name__ == 'f'
    assert g.gi_frame is not None
    assert not g.gi_running
    g.next()
    assert not g.gi_running
    with raises(StopIteration):
        g.next()
    assert not g.gi_running
    assert g.gi_frame is None
    assert g.gi_code is f.__code__
    assert g.__name__ == 'f'

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
    g.next()
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
    assert g.next() == 1
    assert g.throw(NameError("Error")) == 3
    with raises(StopIteration):
        g.next()

def test_throw4():
    def f():
        try:
            yield 1
            v = (yield 2)
        except NameError:
            yield 3
    g = f()
    assert g.next() == 1
    assert g.next() == 2
    assert g.throw(NameError("Error")) == 3
    with raises(StopIteration):
        g.next()

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
    g.next()
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
    res = g.next()
    assert res == 1
    with raises(StopIteration):
        g.next()
    with raises(NameError):
        g.throw(NameError)

def test_close():
    def f():
        yield 1
    g = f()
    assert g.close() is None

def test_close2():
    def f():
        try:
            yield 1
        except GeneratorExit:
            raise StopIteration
    g = f()
    g.next()
    assert g.close() is None

def test_close3():
    def f():
        try:
            yield 1
        except GeneratorExit:
            raise NameError
    g = f()
    g.next()
    with raises(NameError):
        g.close()

def test_close_fail():
    def f():
        try:
            yield 1
        except GeneratorExit:
            yield 2
    g = f()
    g.next()
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
    g.next()
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

def test_generator_explicit_stopiteration():
    def f():
        yield 1
        raise StopIteration
    g = f()
    assert [x for x in g] == [1]

def test_generator_propagate_stopiteration():
    def f():
        it = iter([1])
        while 1:
            yield it.next()
    g = f()
    assert [x for x in g] == [1]

def test_generator_restart():
    def g():
        i = me.next()
        yield i
    me = g()
    with raises(ValueError):
        me.next()

def test_generator_expression():
    exec "res = sum(i*i for i in range(5))"
    assert res == 30

def test_generator_expression_2():
    def f():
        total = sum(i for i in [x for x in z])
        return total, x
    z = [1, 2, 7]
    assert f() == (10, 7)

def test_repr():
    def myFunc():
        yield 1
    g = myFunc()
    r = repr(g)
    assert r.startswith("<generator object myFunc at 0x")
    assert list(g) == [1]
    assert repr(g) == r

def test_unpackiterable_gen():
    g = (i * i for i in range(-5, 3))
    assert set(g) == set([0, 1, 4, 9, 16, 25])
    assert set(g) == set()
    assert set(i for i in range(0)) == set()

def test_explicit_stop_iteration_unpackiterable():
    def f():
        yield 1
        raise StopIteration
    assert tuple(f()) == (1,)

def test_exception_is_cleared_by_yield():
    def f():
        try:
            foobar
        except NameError:
            yield 5
            raise    # should raise "no active exception to re-raise"
    gen = f()
    next(gen)  # --> 5
    try:
        next(gen)
    except TypeError:
        pass

def test_multiple_invalid_sends():
    def mygen():
        yield 42
    g = mygen()
    with raises(TypeError):
        g.send(2)
    with raises(TypeError):
        g.send(2)
