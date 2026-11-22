"""Non-local control flow: break, continue, return and exceptions
crossing try/except, try/finally and with blocks. The graphs must
behave like the Python functions."""
import py

from rpython.rtyper.test.tool import BaseRtypingTest


def check(x):
    if x == 7:
        raise ValueError
    return x * 2

def may_raise(x):
    if x > 5:
        raise ValueError
    return x

class Ctx(object):
    def __init__(self):
        self.log = 0

    def __enter__(self):
        self.log = self.log * 10 + 1
        return self

    def __exit__(self, typ, value, tb):
        if typ is None:
            self.log = self.log * 10 + 2
        else:
            self.log = self.log * 10 + 3

def loop_finally(n, stop):
    total = 0
    for x in range(-2, n):
        try:
            try:
                if x < 0:
                    continue
                if x == stop:
                    break
                if x > 50:
                    return -1
                total += check(x)
            except ValueError:
                total -= 100
        finally:
            total += 1
    return total

def while_else(n):
    i = 0
    res = 0
    while i < n:
        i += 1
        try:
            if i % 3 == 0:
                continue
            if i == 10:
                break
            res += i
        finally:
            res *= 2
    else:
        res += 1000
    return res

def with_flow(n):
    c = Ctx()
    for i in range(n):
        try:
            with c:
                if i == 1:
                    continue
                if i == 2:
                    check(7)
                if i == 3:
                    break
        except ValueError:
            c.log = c.log * 10 + 9
    return c.log

def reraise(n):
    try:
        try:
            check(n)
        except ValueError:
            if n > 5:
                raise
            return 1
    except ValueError:
        return 2
    return 3

def finally_override(n):
    try:
        if n == 1:
            return 1
        check(n)
    finally:
        if n > 1:
            return 2
    return 3

def call_finally_override(n):
    try:
        return finally_override(n)
    except ValueError:
        return -1

def except_in_loop(n):
    res = 0
    i = 0
    while True:
        i += 1
        try:
            res += check(i)
        except ValueError:
            if n:
                break
            res += 1000
        else:
            if i > 9:
                return res
    return -res

def break_in_finally_in_try(x):
    n = 0
    while n < 3:
        n += 1
        try:
            try:
                if may_raise(x) == 2:
                    break
            finally:
                if x == 7:
                    return 7
        except ValueError:
            x -= 1
    return n * 100 + x

def return_in_nested_finally(x):
    try:
        try:
            return may_raise(x)
        finally:
            x += 1
            if x == 3:
                return 30
    finally:
        if x == 5:
            return 50

def break_in_finally(x):
    n = 0
    while True:
        try:
            n += 1
            if n > x:
                return n
        finally:
            if n == 3:
                break
    return -n

def break_and_continue_in_nested_loops(x):
    n = 0
    for i in range(3):
        for j in range(3):
            try:
                if j == x:
                    break
                if i == x:
                    continue
                n += 1
            finally:
                n += 10
    return n

def return_in_nested_with(x):
    c = Ctx()
    try:
        with c:
            with c:
                if x:
                    return c.log
                may_raise(x + 10)
    except ValueError:
        pass
    return -c.log

def try_except_in_finally(x):
    n = 0
    try:
        return may_raise(x)
    finally:
        try:
            may_raise(x + 3)
        except ValueError:
            n += 1
        x += n

def break_in_try_except(x):
    while x:
        try:
            if may_raise(x) == 3:
                break
        except ValueError:
            pass
        x -= 1
    return x

def loop_in_finally(x):
    try:
        return may_raise(x)
    finally:
        while x > 0:
            x -= 1


class TestControlFlow(BaseRtypingTest):
    @py.test.mark.parametrize('n, stop',
                              [(5, 99), (10, 3), (10, 99), (60, 99)])
    def test_loop_finally(self, n, stop):
        res = self.interpret(loop_finally, [n, stop])
        assert res == loop_finally(n, stop)

    @py.test.mark.parametrize('n', [0, 5, 12])
    def test_while_else(self, n):
        assert self.interpret(while_else, [n]) == while_else(n)

    @py.test.mark.parametrize('n', [1, 2, 3, 5])
    def test_with_flow(self, n):
        assert self.interpret(with_flow, [n]) == with_flow(n)

    @py.test.mark.parametrize('n', [1, 7])
    def test_reraise(self, n):
        assert self.interpret(reraise, [n]) == reraise(n)

    @py.test.mark.parametrize('n', [0, 1, 2, 7])
    def test_finally_override(self, n):
        res = self.interpret(call_finally_override, [n])
        assert res == call_finally_override(n)

    @py.test.mark.parametrize('n', [0, 1])
    def test_except_in_loop(self, n):
        assert self.interpret(except_in_loop, [n]) == except_in_loop(n)

    @py.test.mark.parametrize('func', [
        break_in_finally_in_try, return_in_nested_finally, break_in_finally,
        break_and_continue_in_nested_loops, return_in_nested_with,
        try_except_in_finally, break_in_try_except, loop_in_finally])
    def test_through_handlers(self, func):
        def f(x):
            try:
                return func(x)
            except ValueError:
                return -1
        for x in range(9):
            assert self.interpret(f, [x]) == f(x)
