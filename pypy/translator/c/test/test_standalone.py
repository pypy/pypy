from pypy.translator.translator import Translator
from pypy.translator.tool.cbuild import build_executable 
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
from pypy.rpython.objectmodel import stack_frames_depth, stack_too_big
import os


def test_hello_world():
    def entry_point(argv):
        os.write(1, "hello world\n")
        argv = argv[1:]
        os.write(1, "argument count: " + str(len(argv)) + "\n")
        for s in argv:
            os.write(1, "   '" + str(s) + "'\n")
        return 0
    
    t = Translator(entry_point)
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    t.annotate([s_list_of_strings])
    t.specialize()
    cbuilder = t.cbuilder(standalone=True)
    cbuilder.generate_source()
    cbuilder.compile() 
    data = cbuilder.cmdexec('hi there')
    assert data.startswith('''hello world\nargument count: 2\n   'hi'\n   'there'\n''')


def test_stack_unwind():
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
    assert eval(data) == [10, 5.500000, 1, 2]


def test_stack_too_big():
    def f(n):
        if stack_too_big():
            return n
        return f(n+1)

    def fn():
        return f(0)
    data = wrap_stackless_function(fn)
    assert int(data.strip()) > 500


    
def wrap_stackless_function(fn):
    def entry_point(argv):
        os.write(1, str(fn())+"\n")
        return 0

    t = Translator(entry_point)
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    t.annotate([s_list_of_strings])
    t.specialize()
    cbuilder = t.cbuilder(standalone=True)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile() 
    return cbuilder.cmdexec('')
