from pypy.translator.translator import Translator
from pypy.translator.tool.cbuild import build_executable 
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
from pypy.rpython.objectmodel import stack_frames_depth
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

def INPROGRESStest_stack_withptr():
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
