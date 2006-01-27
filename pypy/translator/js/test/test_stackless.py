import py

from pypy.rpython.rstack import stack_unwind, stack_frames_depth, stack_too_big
from pypy.rpython.rstack import yield_current_frame_to_caller
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rjs import jseval 
from pypy.translator.js.test.runtest import compile_function
from pypy.translator.js import conftest

def wrap_stackless_function(fn):
    jsfn = compile_function(fn, [], stackless=True)
    return str(jsfn()) + "\n"

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
    py.test.skip("[Object object] unknown failure")
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
    assert int(data.strip()) > 50   #conservative estimate because the value is browser dependent


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
        return f(10**4)
    data = wrap_stackless_function(fn)
    assert int(data.strip()) == 697 #10**4==697(6seconds, 10**5==545(45seconds)

def test_yield_frame1():
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

def test_yield_frame2():
    S = lltype.GcStruct("base", ('a', lltype.Signed))
    s = lltype.malloc(S)

    def g(x):
        x.a <<= 2
        frametop_before_5 = yield_current_frame_to_caller()
        x.a <<= 4
        frametop_before_7 = frametop_before_5.switch()
        x.a <<= 6
        return frametop_before_7

    def f():
        s.a = 1
        frametop_before_4 = g(s)
        s.a += 3
        frametop_before_6 = frametop_before_4.switch()
        s.a += 5
        frametop_after_return = frametop_before_6.switch()
        s.a += 7
        assert frametop_after_return is None
        return s.a

    data = wrap_stackless_function(f)
    assert int(data.strip()) == 7495

# XXX
# need test to detect timeout (return=undefined), call slp_main_loop() until no timeout
# and only then check result.

def test_long_running():
    if not conftest.option.jsbrowser:
            py.test.skip("works only in a browser (use py.test --browser)") 

    start_time = lltype.malloc(lltype.GcArray(lltype.Signed), 1) 

    def getTime():
        return int(jseval("Math.floor(new Date().getTime())"))

    def g(n):
        for i in range(10):
            pass
        if getTime() - start_time[0] < 10*1000:
            x = g(n-1)
            if x != n-1:
                jseval("log('x != n-1')")
        return n

    def lp():
        start_time[0] = getTime()
        return g(100000)

    data = wrap_stackless_function(lp)

    #note: because long running processes can't return a value like this
    assert int(data.strip()) == undefined
