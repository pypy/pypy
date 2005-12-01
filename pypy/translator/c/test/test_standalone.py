from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.model import SomeList, SomeString
from pypy.annotation.listdef import ListDef
import os


def test_hello_world():
    def entry_point(argv):
        os.write(1, "hello world\n")
        argv = argv[1:]
        os.write(1, "argument count: " + str(len(argv)) + "\n")
        for s in argv:
            os.write(1, "   '" + str(s) + "'\n")
        return 0

    s_list_of_strings = SomeList(ListDef(None, SomeString()))
    s_list_of_strings.listdef.resize()
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.generate_source()
    cbuilder.compile()
    data = cbuilder.cmdexec('hi there')
    assert data.startswith('''hello world\nargument count: 2\n   'hi'\n   'there'\n''')
