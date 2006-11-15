import py
import sys, os

from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.listdef import s_list_of_strings
from pypy.tool.udir import udir


def test_hello_world():
    def entry_point(argv):
        os.write(1, "hello world\n")
        argv = argv[1:]
        os.write(1, "argument count: " + str(len(argv)) + "\n")
        for s in argv:
            os.write(1, "   '" + str(s) + "'\n")
        return 0

    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.generate_source()
    cbuilder.compile()
    data = cbuilder.cmdexec('hi there')
    assert data.startswith('''hello world\nargument count: 2\n   'hi'\n   'there'\n''')

def test_print():
    def entry_point(argv):
        print "hello simpler world"
        argv = argv[1:]
        print "argument count:", len(argv)
        print "arguments:", argv
        print "argument lengths:",
        print [len(s) for s in argv]
        return 0

    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    cbuilder = CStandaloneBuilder(t, entry_point)
    cbuilder.generate_source()
    cbuilder.compile()
    data = cbuilder.cmdexec('hi there')
    assert data.startswith('''hello simpler world\n'''
                           '''argument count: 2\n'''
                           '''arguments: [hi, there]\n'''
                           '''argument lengths: [2, 5]\n''')
    # NB. RPython has only str, not repr, so str() on a list of strings
    # gives the strings unquoted in the list

def test_counters():
    if sys.platform != 'linux2':
        py.test.skip("instrument counters support is unix only for now")
    from pypy.rpython.lltypesystem import lltype
    from pypy.rpython.lltypesystem.lloperation import llop
    def entry_point(argv):
        llop.instrument_count(lltype.Void, 'test', 2)
        llop.instrument_count(lltype.Void, 'test', 1)
        llop.instrument_count(lltype.Void, 'test', 1)
        llop.instrument_count(lltype.Void, 'test', 2)
        llop.instrument_count(lltype.Void, 'test', 1)        
        return 0
    t = TranslationContext()
    t.config.translation.instrument = True
    t.buildannotator().build_types(entry_point, [s_list_of_strings])
    t.buildrtyper().specialize()

    cbuilder = CStandaloneBuilder(t, entry_point, config=t.config) # xxx
    cbuilder.generate_source()
    cbuilder.compile()

    counters_fname = udir.join("_counters_")
    os.putenv('_INSTRUMENT_COUNTERS', str(counters_fname))
    try:
        data = cbuilder.cmdexec()
    finally:
        os.unsetenv('_INSTRUMENT_COUNTERS')

    f = counters_fname.open('rb')
    counters_data = f.read()
    f.close()

    import struct
    counters = struct.unpack("LLL", counters_data)

    assert counters == (0,3,2)
