from pypy.translator.translator import Translator
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
from pypy.rpython.rstack import stack_unwind, stack_frames_depth, stack_too_big
from pypy.rpython.rstack import yield_current_frame_to_caller
import os

def wrap_stackless_function(fn):
    def entry_point(argv):
        os.write(1, str(fn())+"\n")
        return 0

    t = Translator(entry_point)
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    ann = t.annotate([s_list_of_strings])
    t.specialize()
    cbuilder = t.cbuilder(standalone=True)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile()
    return cbuilder.cmdexec('')

# ____________________________________________________________

def test_stack_depth():
    def g1():
        "just to check Void special cases around the code"
    def g2(ignored):
        g1()
    def f(n):
        g1()
        if n > 0:
            res = f(n-1)
        else:
            res = stack_frames_depth()
        g2(g1)
        return res

    def fn():
        count0 = f(0)
        count10 = f(10)
        return count10 - count0

    data = wrap_stackless_function(fn)
    assert data.strip() == '10'

def test_stack_withptr():
    def f(n):
        if n > 0:
            res = f(n-1)
        else:
            res = stack_frames_depth(), 1
        return res

    def fn():
        count0, _ = f(0)
        count10, _ = f(10)
        return count10 - count0

    data = wrap_stackless_function(fn)
    assert data.strip() == '10'

def test_stackless_manytimes():
    def f(n):
        if n > 0:
            stack_frames_depth()
            res = f(n-1)
        else:
            res = stack_frames_depth(), 1
        return res

    def fn():
        count0, _ = f(0)
        count10, _ = f(100)
        return count10 - count0

    data = wrap_stackless_function(fn)
    assert data.strip() == '100'

def test_stackless_arguments():
    def f(n, d, t):
        if n > 0:
            res = f(n-1, d, t)
        else:
            res = stack_frames_depth(), d, t
        return res

    def fn():
        count0, d, t = f(0, 5.5, (1, 2))
        count10, d, t = f(10, 5.5, (1, 2))
        return "[" + str(count10 - count0) + ", " + str(d) + ", " + str(t[0]) + ", " + str(t[1]) + "]"

    data = wrap_stackless_function(fn)
    assert eval(data) == [10, 5.5, 1, 2]


def test_stack_too_big():
    def f1():
        return stack_too_big()
    def f2():
        return lst[1]()
    def f3():
        return lst[2]()
    def f4():
        return lst[3]()
    def f5():
        return lst[4]()
    lst = [None,f1,f2,f3,f4,f5]

    def f(n):
        if lst[5]():
            return n
        return f(n)+1

    def fn():
        return f(0)
    data = wrap_stackless_function(fn)
    assert int(data.strip()) > 500


def test_stack_unwind():
    def f():
        stack_unwind()
        return 42

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 42

def test_auto_stack_unwind():
    def f(n):
        if n == 1:
            return 1
        return (n+f(n-1)) % 1291

    def fn():
        return f(10**6)
    data = wrap_stackless_function(fn)
    assert int(data.strip()) == 704


def test_yield_frame():

    def g(lst):
        lst.append(2)
        frametop_before_5 = yield_current_frame_to_caller()
        lst.append(4)
        frametop_before_7 = frametop_before_5.switch()
        lst.append(6)
        return frametop_before_7

    def f():
        lst = [1]
        frametop_before_4 = g(lst)
        lst.append(3)
        frametop_before_6 = frametop_before_4.switch()
        lst.append(5)
        frametop_after_return = frametop_before_6.switch()
        lst.append(7)
        assert frametop_after_return is None
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 1234567

def test_yield_noswitch_frame():
    # this time we make sure that function 'g' does not
    # need to switch and even does not need to be stackless

    def g(lst):
        lst.append(2)
        frametop_before_5 = yield_current_frame_to_caller()
        lst.append(4)
        return frametop_before_5

    def f():
        lst = [1]
        frametop_before_4 = g(lst)
        lst.append(3)
        frametop_after_return = frametop_before_4.switch()
        lst.append(5)
        assert frametop_after_return is None
        n = 0
        for i in lst:
            n = n*10 + i
        return n

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 12345
