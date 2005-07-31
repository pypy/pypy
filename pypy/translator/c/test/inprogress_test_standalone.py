from pypy.translator.translator import Translator
from pypy.translator.tool.cbuild import build_executable 
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
import os


def test_hello_world():
    def entry_point(argv):
        os.write(1, "hello world\n")
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
    XXX 
