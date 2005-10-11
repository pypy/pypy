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


def INPROGRESS_test_stack_unwind():
    def f(n):
        if n > 0:
            return f(n-1)
        else:
            return stack_frames_depth()
    def entry_point(argv):
        count0 = f(0)
        count10 = f(10)
        diff = count10 - count0
        os.write(1, str(diff)+"\n")
        return 0

    t = Translator(entry_point)
    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    t.annotate([s_list_of_strings])
    t.specialize()
    cbuilder = t.cbuilder(standalone=True)
    cbuilder.stackless = True
    cbuilder.generate_source()
    cbuilder.compile() 
    data = cbuilder.cmdexec('')
    assert data.strip() == '10'
