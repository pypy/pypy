import py
import sys, os, re

from pypy.rlib.objectmodel import keepalive_until_here
from pypy.rlib.rarithmetic import r_longlong
from pypy.rlib.debug import ll_assert, have_debug_prints, debug_flush
from pypy.rlib.debug import debug_print, debug_start, debug_stop, debug_offset
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt import all
from pypy.translator.c.genc import CStandaloneBuilder, ExternalCompilationInfo
from pypy.annotation.listdef import s_list_of_strings
from pypy.tool.udir import udir
from pypy.tool.autopath import pypydir
from pypy.conftest import option


class StandaloneTests(object):
    config = None

    def compile(self, entry_point, debug=True, shared=False,
                stackcheck=False):
        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        if stackcheck:
            from pypy.translator.transform import insert_ll_stackcheck
            insert_ll_stackcheck(t)

        t.config.translation.shared = shared

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        if debug:
            cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        else:
            cbuilder.generate_source()
        cbuilder.compile()
        if option.view:
            t.view()
        return t, cbuilder


class TestStandalone(StandaloneTests):

    def test_hello_world(self):
        def entry_point(argv):
            os.write(1, "hello world\n")
            argv = argv[1:]
            os.write(1, "argument count: " + str(len(argv)) + "\n")
            for s in argv:
                os.write(1, "   '" + str(s) + "'\n")
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert data.startswith('''hello world\nargument count: 2\n   'hi'\n   'there'\n''')

    def test_print(self):
        def entry_point(argv):
            print "hello simpler world"
            argv = argv[1:]
            print "argument count:", len(argv)
            print "arguments:", argv
            print "argument lengths:",
            print [len(s) for s in argv]
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert data.startswith('''hello simpler world\n'''
                               '''argument count: 2\n'''
                               '''arguments: [hi, there]\n'''
                               '''argument lengths: [2, 5]\n''')
        # NB. RPython has only str, not repr, so str() on a list of strings
        # gives the strings unquoted in the list

    def test_counters(self):
        from pypy.rpython.lltypesystem import lltype
        from pypy.rpython.lltypesystem.lloperation import llop
        def entry_point(argv):
            llop.instrument_count(lltype.Void, 'test', 2)
            llop.instrument_count(lltype.Void, 'test', 1)
            llop.instrument_count(lltype.Void, 'test', 1)
            llop.instrument_count(lltype.Void, 'test', 2)
            llop.instrument_count(lltype.Void, 'test', 1)        
            return 0
        t = TranslationContext(self.config)
        t.config.translation.instrument = True
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, config=t.config) # xxx
        cbuilder.generate_source()
        cbuilder.compile()

        counters_fname = udir.join("_counters_")
        os.environ['_INSTRUMENT_COUNTERS'] = str(counters_fname)
        try:
            data = cbuilder.cmdexec()
        finally:
            del os.environ['_INSTRUMENT_COUNTERS']

        f = counters_fname.open('rb')
        counters_data = f.read()
        f.close()

        import struct
        counters = struct.unpack("LLL", counters_data)

        assert counters == (0,3,2)

    def test_prof_inline(self):
        py.test.skip("broken by 5b0e029514d4, but we don't use it any more")
        if sys.platform == 'win32':
            py.test.skip("instrumentation support is unix only for now")
        def add(a,b):
            return a + b - b + b - b + b - b + b - b + b - b + b - b + b
        def entry_point(argv):
            tot =  0
            x = int(argv[1])
            while x > 0:
                tot = add(tot, x)
                x -= 1
            os.write(1, str(tot))
            return 0
        from pypy.translator.interactive import Translation
        t = Translation(entry_point, backend='c', standalone=True)
        # no counters
        t.backendopt(inline_threshold=100, profile_based_inline="500")
        exe = t.compile()
        out = py.process.cmdexec("%s 500" % exe)
        assert int(out) == 500*501/2

        t = Translation(entry_point, backend='c', standalone=True)
        # counters
        t.backendopt(inline_threshold=all.INLINE_THRESHOLD_FOR_TEST*0.5,
                     profile_based_inline="500")
        exe = t.compile()
        out = py.process.cmdexec("%s 500" % exe)
        assert int(out) == 500*501/2

    def test_frexp(self):
        import math
        def entry_point(argv):
            m, e = math.frexp(0)
            x, y = math.frexp(0)
            print m, x
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert map(float, data.split()) == [0.0, 0.0]

    def test_profopt(self):
        def add(a,b):
            return a + b - b + b - b + b - b + b - b + b - b + b - b + b
        def entry_point(argv):
            tot =  0
            x = int(argv[1])
            while x > 0:
                tot = add(tot, x)
                x -= 1
            os.write(1, str(tot))
            return 0
        from pypy.translator.interactive import Translation
        # XXX this is mostly a "does not crash option"
        t = Translation(entry_point, backend='c', standalone=True, profopt="100")
        # no counters
        t.backendopt()
        exe = t.compile()
        out = py.process.cmdexec("%s 500" % exe)
        assert int(out) == 500*501/2
        t = Translation(entry_point, backend='c', standalone=True, profopt="100",
                        noprofopt=True)
        # no counters
        t.backendopt()
        exe = t.compile()
        out = py.process.cmdexec("%s 500" % exe)
        assert int(out) == 500*501/2

    if hasattr(os, 'setpgrp'):
        def test_os_setpgrp(self):
            def entry_point(argv):
                os.setpgrp()
                return 0

            t, cbuilder = self.compile(entry_point)
            cbuilder.cmdexec("")


    def test_profopt_mac_osx_bug(self):
        if sys.platform == 'win32':
            py.test.skip("no profopt on win32")
        def entry_point(argv):
            import os
            pid = os.fork()
            if pid:
                os.waitpid(pid, 0)
            else:
                os._exit(0)
            return 0
        from pypy.translator.interactive import Translation
        # XXX this is mostly a "does not crash option"
        t = Translation(entry_point, backend='c', standalone=True, profopt="")
        # no counters
        t.backendopt()
        exe = t.compile()
        #py.process.cmdexec(exe)
        t = Translation(entry_point, backend='c', standalone=True, profopt="",
                        noprofopt=True)
        # no counters
        t.backendopt()
        exe = t.compile()
        #py.process.cmdexec(exe)

    def test_standalone_large_files(self):
        filename = str(udir.join('test_standalone_largefile'))
        r4800000000 = r_longlong(4800000000L)
        def entry_point(argv):
            assert str(r4800000000 + len(argv)) == '4800000003'
            fd = os.open(filename, os.O_RDWR | os.O_CREAT, 0644)
            os.lseek(fd, r4800000000, 0)
            newpos = os.lseek(fd, 0, 1)
            if newpos == r4800000000:
                print "OK"
            else:
                print "BAD POS"
            os.close(fd)
            return 0
        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('hi there')
        assert data.strip() == "OK"

    def test_separate_files(self):
        # One file in translator/c/src
        fname = py.path.local(pypydir).join(
            'translator', 'c', 'src', 'll_strtod.h')

        # One file in (another) subdir of the temp directory
        dirname = udir.join("test_dir").ensure(dir=1)
        fname2 = dirname.join("test_genc.c")
        fname2.write("""
        void f() {
            LL_strtod_formatd(12.3, 'f', 5);
        }""")

        files = [fname, fname2]

        def entry_point(argv):
            return 0

        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.eci = cbuilder.eci.merge(
            ExternalCompilationInfo(separate_module_files=files))
        cbuilder.generate_source()

        makefile = udir.join(cbuilder.modulename, 'Makefile').read()

        # generated files are compiled in the same directory
        assert "  ../test_dir/test_genc.c" in makefile
        assert "  ../test_dir/test_genc.o" in makefile

        # but files from pypy source dir must be copied
        assert "translator/c/src" not in makefile
        assert "  ll_strtod.h" in makefile
        assert "  ll_strtod.o" in makefile

    def test_debug_print_start_stop(self):
        def entry_point(argv):
            x = "got:"
            debug_start  ("mycat")
            if have_debug_prints(): x += "b"
            debug_print    ("foo", r_longlong(2), "bar", 3)
            debug_start      ("cat2")
            if have_debug_prints(): x += "c"
            debug_print        ("baz")
            debug_stop       ("cat2")
            if have_debug_prints(): x += "d"
            debug_print    ("bok")
            debug_stop   ("mycat")
            if have_debug_prints(): x += "a"
            debug_print("toplevel")
            debug_flush()
            os.write(1, x + "." + str(debug_offset()) + '.\n')
            return 0
        t, cbuilder = self.compile(entry_point)
        # check with PYPYLOG undefined
        out, err = cbuilder.cmdexec("", err=True, env={})
        assert out.strip() == 'got:a.-1.'
        assert 'toplevel' in err
        assert 'mycat' not in err
        assert 'foo 2 bar 3' not in err
        assert 'cat2' not in err
        assert 'baz' not in err
        assert 'bok' not in err
        # check with PYPYLOG defined to an empty string (same as undefined)
        out, err = cbuilder.cmdexec("", err=True, env={'PYPYLOG': ''})
        assert out.strip() == 'got:a.-1.'
        assert 'toplevel' in err
        assert 'mycat' not in err
        assert 'foo 2 bar 3' not in err
        assert 'cat2' not in err
        assert 'baz' not in err
        assert 'bok' not in err
        # check with PYPYLOG=:- (means print to stderr)
        out, err = cbuilder.cmdexec("", err=True, env={'PYPYLOG': ':-'})
        assert out.strip() == 'got:bcda.-1.'
        assert 'toplevel' in err
        assert '{mycat' in err
        assert 'mycat}' in err
        assert 'foo 2 bar 3' in err
        assert '{cat2' in err
        assert 'cat2}' in err
        assert 'baz' in err
        assert 'bok' in err
        # check with PYPYLOG=:somefilename
        path = udir.join('test_debug_xxx.log')
        out, err = cbuilder.cmdexec("", err=True,
                                    env={'PYPYLOG': ':%s' % path})
        size = os.stat(str(path)).st_size
        assert out.strip() == 'got:bcda.' + str(size) + '.'
        assert not err
        assert path.check(file=1)
        data = path.read()
        assert 'toplevel' in data
        assert '{mycat' in data
        assert 'mycat}' in data
        assert 'foo 2 bar 3' in data
        assert '{cat2' in data
        assert 'cat2}' in data
        assert 'baz' in data
        assert 'bok' in data
        # check with PYPYLOG=somefilename
        path = udir.join('test_debug_xxx_prof.log')
        out, err = cbuilder.cmdexec("", err=True, env={'PYPYLOG': str(path)})
        size = os.stat(str(path)).st_size
        assert out.strip() == 'got:a.' + str(size) + '.'
        assert not err
        assert path.check(file=1)
        data = path.read()
        assert 'toplevel' in data
        assert '{mycat' in data
        assert 'mycat}' in data
        assert 'foo 2 bar 3' not in data
        assert '{cat2' in data
        assert 'cat2}' in data
        assert 'baz' not in data
        assert 'bok' not in data
        # check with PYPYLOG=myc:somefilename   (includes mycat but not cat2)
        path = udir.join('test_debug_xxx_myc.log')
        out, err = cbuilder.cmdexec("", err=True,
                                    env={'PYPYLOG': 'myc:%s' % path})
        size = os.stat(str(path)).st_size
        assert out.strip() == 'got:bda.' + str(size) + '.'
        assert not err
        assert path.check(file=1)
        data = path.read()
        assert 'toplevel' in data
        assert '{mycat' in data
        assert 'mycat}' in data
        assert 'foo 2 bar 3' in data
        assert 'cat2' not in data
        assert 'baz' not in data
        assert 'bok' in data
        # check with PYPYLOG=cat:somefilename   (includes cat2 but not mycat)
        path = udir.join('test_debug_xxx_cat.log')
        out, err = cbuilder.cmdexec("", err=True,
                                    env={'PYPYLOG': 'cat:%s' % path})
        size = os.stat(str(path)).st_size
        assert out.strip() == 'got:ca.' + str(size) + '.'
        assert not err
        assert path.check(file=1)
        data = path.read()
        assert 'toplevel' in data
        assert 'mycat' not in data
        assert 'foo 2 bar 3' not in data
        assert 'cat2' in data
        assert 'baz' in data
        assert 'bok' not in data
        # check with PYPYLOG=myc,cat2:somefilename   (includes mycat and cat2)
        path = udir.join('test_debug_xxx_myc_cat2.log')
        out, err = cbuilder.cmdexec("", err=True,
                                    env={'PYPYLOG': 'myc,cat2:%s' % path})
        size = os.stat(str(path)).st_size
        assert out.strip() == 'got:bcda.' + str(size) + '.'
        assert not err
        assert path.check(file=1)
        data = path.read()
        assert 'toplevel' in data
        assert '{mycat' in data
        assert 'mycat}' in data
        assert 'foo 2 bar 3' in data
        assert 'cat2' in data
        assert 'baz' in data
        assert 'bok' in data
        #
        # finally, check compiling with logging disabled
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.log = False
        self.config = config
        t, cbuilder = self.compile(entry_point)
        path = udir.join('test_debug_does_not_show_up.log')
        out, err = cbuilder.cmdexec("", err=True,
                                    env={'PYPYLOG': ':%s' % path})
        assert out.strip() == 'got:.-1.'
        assert not err
        assert path.check(file=0)

    def test_debug_print_start_stop_nonconst(self):
        def entry_point(argv):
            debug_start(argv[1])
            debug_print(argv[2])
            debug_stop(argv[1])
            return 0
        t, cbuilder = self.compile(entry_point)
        out, err = cbuilder.cmdexec("foo bar", err=True, env={'PYPYLOG': ':-'})
        lines = err.splitlines()
        assert '{foo' in lines[0]
        assert 'bar' == lines[1]
        assert 'foo}' in lines[2]


    def test_fatal_error(self):
        def g(x):
            if x == 1:
                raise ValueError
            else:
                raise KeyError
        def entry_point(argv):
            if len(argv) < 3:
                g(len(argv))
            return 0
        t, cbuilder = self.compile(entry_point)
        #
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        idx = lines.index('Fatal RPython error: ValueError')   # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 4
        l0, l1, l2 = lines[-4:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in entry_point', l1)
        assert re.match(r'  File "\w+.c", line \d+, in g', l2)
        #
        out2, err2 = cbuilder.cmdexec("x", expect_crash=True)
        assert out2.strip() == ''
        lines2 = err2.strip().splitlines()
        idx = lines2.index('Fatal RPython error: KeyError')    # assert found
        lines2 = lines2[:idx+1]
        l0, l1, l2 = lines2[-4:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in entry_point', l1)
        assert re.match(r'  File "\w+.c", line \d+, in g', l2)
        assert lines2[-2] != lines[-2]    # different line number
        assert lines2[-3] == lines[-3]    # same line number

    def test_fatal_error_finally_1(self):
        # a simple case of try:finally:
        def g(x):
            if x == 1:
                raise KeyError
        def h(x):
            try:
                g(x)
            finally:
                os.write(1, 'done.\n')
        def entry_point(argv):
            if len(argv) < 3:
                h(len(argv))
            return 0
        t, cbuilder = self.compile(entry_point)
        #
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == 'done.'
        lines = err.strip().splitlines()
        idx = lines.index('Fatal RPython error: KeyError')    # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 5
        l0, l1, l2, l3 = lines[-5:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in entry_point', l1)
        assert re.match(r'  File "\w+.c", line \d+, in h', l2)
        assert re.match(r'  File "\w+.c", line \d+, in g', l3)

    def test_fatal_error_finally_2(self):
        # a try:finally: in which we raise and catch another exception
        def raiseme(x):
            if x == 1:
                raise ValueError
        def raise_and_catch(x):
            try:
                raiseme(x)
            except ValueError:
                pass
        def g(x):
            if x == 1:
                raise KeyError
        def h(x):
            try:
                g(x)
            finally:
                raise_and_catch(x)
                os.write(1, 'done.\n')
        def entry_point(argv):
            if len(argv) < 3:
                h(len(argv))
            return 0
        t, cbuilder = self.compile(entry_point)
        #
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == 'done.'
        lines = err.strip().splitlines()
        idx = lines.index('Fatal RPython error: KeyError')     # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 5
        l0, l1, l2, l3 = lines[-5:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in entry_point', l1)
        assert re.match(r'  File "\w+.c", line \d+, in h', l2)
        assert re.match(r'  File "\w+.c", line \d+, in g', l3)

    def test_fatal_error_finally_3(self):
        py.test.skip("not implemented: "
                     "a try:finally: in which we raise the *same* exception")

    def test_fatal_error_finally_4(self):
        # a try:finally: in which we raise (and don't catch) an exception
        def raiseme(x):
            if x == 1:
                raise ValueError
        def g(x):
            if x == 1:
                raise KeyError
        def h(x):
            try:
                g(x)
            finally:
                raiseme(x)
                os.write(1, 'done.\n')
        def entry_point(argv):
            if len(argv) < 3:
                h(len(argv))
            return 0
        t, cbuilder = self.compile(entry_point)
        #
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        idx = lines.index('Fatal RPython error: ValueError')    # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 5
        l0, l1, l2, l3 = lines[-5:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in entry_point', l1)
        assert re.match(r'  File "\w+.c", line \d+, in h', l2)
        assert re.match(r'  File "\w+.c", line \d+, in raiseme', l3)

    def test_assertion_error_debug(self):
        def entry_point(argv):
            assert len(argv) != 1
            return 0
        t, cbuilder = self.compile(entry_point, debug=True)
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        assert 'in pypy_g_RPyRaiseException: AssertionError' in lines

    def test_assertion_error_nondebug(self):
        def g(x):
            assert x != 1
        def f(argv):
            try:
                g(len(argv))
            finally:
                print 'done'
        def entry_point(argv):
            f(argv)
            return 0
        t, cbuilder = self.compile(entry_point, debug=False)
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        idx = lines.index('Fatal RPython error: AssertionError') # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 4
        l0, l1, l2 = lines[-4:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in f', l1)
        assert re.match(r'  File "\w+.c", line \d+, in g', l2)
        # The traceback stops at f() because it's the first function that
        # captures the AssertionError, which makes the program abort.

    def test_int_lshift_too_large(self):
        from pypy.rlib.rarithmetic import LONG_BIT, LONGLONG_BIT
        def entry_point(argv):
            a = int(argv[1])
            b = int(argv[2])
            print a << b
            return 0

        t, cbuilder = self.compile(entry_point, debug=True)
        out = cbuilder.cmdexec("10 2", expect_crash=False)
        assert out.strip() == str(10 << 2)
        cases = [-4, LONG_BIT, LONGLONG_BIT]
        for x in cases:
            out, err = cbuilder.cmdexec("%s %s" % (1, x), expect_crash=True)
            lines = err.strip()
            assert 'The shift count is outside of the supported range' in lines

    def test_llong_rshift_too_large(self):
        from pypy.rlib.rarithmetic import LONG_BIT, LONGLONG_BIT
        def entry_point(argv):
            a = r_longlong(int(argv[1]))
            b = r_longlong(int(argv[2]))
            print a >> b
            return 0

        t, cbuilder = self.compile(entry_point, debug=True)
        out = cbuilder.cmdexec("10 2", expect_crash=False)
        assert out.strip() == str(10 >> 2)
        out = cbuilder.cmdexec("%s %s" % (-42, LONGLONG_BIT - 1), expect_crash=False)
        assert out.strip() == '-1'
        cases = [-4, LONGLONG_BIT]
        for x in cases:
            out, err = cbuilder.cmdexec("%s %s" % (1, x), expect_crash=True)
            lines = err.strip()
            assert 'The shift count is outside of the supported range' in lines

    def test_ll_assert_error_debug(self):
        def entry_point(argv):
            ll_assert(len(argv) != 1, "foobar")
            return 0
        t, cbuilder = self.compile(entry_point, debug=True)
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        assert 'in pypy_g_entry_point: foobar' in lines

    def test_ll_assert_error_nondebug(self):
        py.test.skip("implement later, maybe: tracebacks even with ll_assert")
        def g(x):
            ll_assert(x != 1, "foobar")
        def f(argv):
            try:
                g(len(argv))
            finally:
                print 'done'
        def entry_point(argv):
            f(argv)
            return 0
        t, cbuilder = self.compile(entry_point)
        out, err = cbuilder.cmdexec("", expect_crash=True)
        assert out.strip() == ''
        lines = err.strip().splitlines()
        idx = lines.index('PyPy assertion failed: foobar')    # assert found
        lines = lines[:idx+1]
        assert len(lines) >= 4
        l0, l1, l2 = lines[-4:-1]
        assert l0 == 'RPython traceback:'
        assert re.match(r'  File "\w+.c", line \d+, in f', l1)
        assert re.match(r'  File "\w+.c", line \d+, in g', l2)
        # The traceback stops at f() because it's the first function that
        # captures the AssertionError, which makes the program abort.

    def test_shared(self, monkeypatch):
        def f(argv):
            print len(argv)
        def entry_point(argv):
            f(argv)
            return 0
        t, cbuilder = self.compile(entry_point, shared=True)
        assert cbuilder.shared_library_name is not None
        assert cbuilder.shared_library_name != cbuilder.executable_name
        monkeypatch.setenv('LD_LIBRARY_PATH',
                           cbuilder.shared_library_name.dirpath())
        out, err = cbuilder.cmdexec("a b")
        assert out == "3"

    def test_gcc_options(self):
        # check that the env var CC is correctly interpreted, even if
        # it contains the compiler name followed by some options.
        if sys.platform == 'win32':
            py.test.skip("only for gcc")

        from pypy.rpython.lltypesystem import lltype, rffi
        dir = udir.ensure('test_gcc_options', dir=1)
        dir.join('someextraheader.h').write('#define someextrafunc() 42\n')
        eci = ExternalCompilationInfo(includes=['someextraheader.h'])
        someextrafunc = rffi.llexternal('someextrafunc', [], lltype.Signed,
                                        compilation_info=eci)

        def entry_point(argv):
            return someextrafunc()

        old_cc = os.environ.get('CC')
        try:
            os.environ['CC'] = 'gcc -I%s' % dir
            t, cbuilder = self.compile(entry_point)
        finally:
            if old_cc is None:
                del os.environ['CC']
            else:
                os.environ['CC'] = old_cc

    def test_inhibit_tail_call(self):
        # the point is to check that the f()->f() recursion stops
        from pypy.rlib.rstackovf import StackOverflow
        def f(n):
            if n <= 0:
                return 42
            return f(n+1)
        def entry_point(argv):
            try:
                return f(1)
            except StackOverflow:
                print 'hi!'
                return 0
        t, cbuilder = self.compile(entry_point, stackcheck=True)
        out = cbuilder.cmdexec("")
        assert out.strip() == "hi!"

    def test_set_length_fraction(self):
        # check for pypy.rlib.rstack._stack_set_length_fraction()
        from pypy.rlib.rstack import _stack_set_length_fraction
        from pypy.rlib.rstackovf import StackOverflow
        class A:
            n = 0
        glob = A()
        def f(n):
            glob.n += 1
            if n <= 0:
                return 42
            return f(n+1)
        def entry_point(argv):
            _stack_set_length_fraction(0.1)
            try:
                return f(1)
            except StackOverflow:
                glob.n = 0
            _stack_set_length_fraction(float(argv[1]))
            try:
                return f(1)
            except StackOverflow:
                print glob.n
                return 0
        t, cbuilder = self.compile(entry_point, stackcheck=True)
        counts = {}
        for fraction in [0.1, 0.4, 1.0]:
            out = cbuilder.cmdexec(str(fraction))
            print 'counts[%s]: %r' % (fraction, out)
            counts[fraction] = int(out.strip())
        #
        assert counts[1.0] >= 1000
        # ^^^ should actually be much more than 1000 for this small test
        assert counts[0.1] < counts[0.4] / 3
        assert counts[0.4] < counts[1.0] / 2
        assert counts[0.1] > counts[0.4] / 7
        assert counts[0.4] > counts[1.0] / 4

    def test_stack_criticalcode(self):
        # check for pypy.rlib.rstack._stack_criticalcode_start/stop()
        from pypy.rlib.rstack import _stack_criticalcode_start
        from pypy.rlib.rstack import _stack_criticalcode_stop
        from pypy.rlib.rstackovf import StackOverflow
        class A:
            pass
        glob = A()
        def f(n):
            if n <= 0:
                return 42
            try:
                return f(n+1)
            except StackOverflow:
                if glob.caught:
                    print 'Oups! already caught!'
                glob.caught = True
                _stack_criticalcode_start()
                critical(100)   # recurse another 100 times here
                _stack_criticalcode_stop()
                return 789
        def critical(n):
            if n > 0:
                n = critical(n - 1)
            return n - 42
        def entry_point(argv):
            glob.caught = False
            print f(1)
            return 0
        t, cbuilder = self.compile(entry_point, stackcheck=True)
        out = cbuilder.cmdexec('')
        assert out.strip() == '789'


class TestMaemo(TestStandalone):
    def setup_class(cls):
        py.test.skip("TestMaemo: tests skipped for now")
        from pypy.translator.platform.maemo import check_scratchbox
        check_scratchbox()
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.platform = 'maemo'
        cls.config = config

    def test_profopt(self):
        py.test.skip("Unsupported")

    def test_prof_inline(self):
        py.test.skip("Unsupported")


class TestThread(object):
    gcrootfinder = 'shadowstack'
    config = None

    def compile(self, entry_point):
        t = TranslationContext(self.config)
        t.config.translation.gc = "semispace"
        t.config.translation.gcrootfinder = self.gcrootfinder
        t.config.translation.thread = True
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()
        #
        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source(defines=cbuilder.DEBUG_DEFINES)
        cbuilder.compile()
        #
        return t, cbuilder


    def test_stack_size(self):
        import time
        from pypy.module.thread import ll_thread
        from pypy.rpython.lltypesystem import lltype
        from pypy.rlib.objectmodel import invoke_around_extcall

        class State:
            pass
        state = State()

        def before():
            debug_print("releasing...")
            ll_assert(not ll_thread.acquire_NOAUTO(state.ll_lock, False),
                      "lock not held!")
            ll_thread.release_NOAUTO(state.ll_lock)
            debug_print("released")
        def after():
            debug_print("waiting...")
            ll_thread.acquire_NOAUTO(state.ll_lock, True)
            debug_print("acquired")

        def recurse(n):
            if n > 0:
                return recurse(n-1)+1
            else:
                time.sleep(0.2)      # invokes before/after
                return 0

        # recurse a lot
        RECURSION = 19500
        if sys.platform == 'win32':
            # If I understand it correctly:
            # - The stack size "reserved" for a new thread is a compile-time
            #   option (by default: 1Mb).  This is a minimum that user code
            #   cannot control.
            # - set_stacksize() only sets the initially "committed" size,
            #   which eventually requires a larger "reserved" size.
            # - The limit below is large enough to exceed the "reserved" size,
            #   for small values of set_stacksize().
            RECURSION = 150 * 1000

        def bootstrap():
            recurse(RECURSION)
            state.count += 1

        def entry_point(argv):
            os.write(1, "hello world\n")
            error = ll_thread.set_stacksize(int(argv[1]))
            if error != 0:
                os.write(2, "set_stacksize(%d) returned %d\n" % (
                    int(argv[1]), error))
                raise AssertionError
            # malloc a bit
            s1 = State(); s2 = State(); s3 = State()
            s1.x = 0x11111111; s2.x = 0x22222222; s3.x = 0x33333333
            # start 3 new threads
            state.ll_lock = ll_thread.allocate_ll_lock()
            after()
            state.count = 0
            invoke_around_extcall(before, after)
            ident1 = ll_thread.start_new_thread(bootstrap, ())
            ident2 = ll_thread.start_new_thread(bootstrap, ())
            ident3 = ll_thread.start_new_thread(bootstrap, ())
            # wait for the 3 threads to finish
            while True:
                if state.count == 3:
                    break
                time.sleep(0.1)      # invokes before/after
            # check that the malloced structures were not overwritten
            assert s1.x == 0x11111111
            assert s2.x == 0x22222222
            assert s3.x == 0x33333333
            os.write(1, "done\n")
            return 0

        t, cbuilder = self.compile(entry_point)

        # recursing should crash with only 32 KB of stack,
        # and it should eventually work with more stack
        for test_kb in [32, 128, 512, 1024, 2048, 4096, 8192, 16384,
                        32768, 65536]:
            print >> sys.stderr, 'Trying with %d KB of stack...' % (test_kb,),
            try:
                data = cbuilder.cmdexec(str(test_kb * 1024))
            except Exception, e:
                if e.__class__ is not Exception:
                    raise
                print >> sys.stderr, 'segfault'
                # got a segfault! try with the next stack size...
            else:
                # it worked
                print >> sys.stderr, 'ok'
                assert data == 'hello world\ndone\n'
                assert test_kb > 32   # it cannot work with just 32 KB of stack
                break    # finish
        else:
            py.test.fail("none of the stack sizes worked")


    def test_thread_and_gc(self):
        import time, gc
        from pypy.module.thread import ll_thread
        from pypy.rpython.lltypesystem import lltype
        from pypy.rlib.objectmodel import invoke_around_extcall

        class State:
            pass
        state = State()

        def before():
            ll_assert(not ll_thread.acquire_NOAUTO(state.ll_lock, False),
                      "lock not held!")
            ll_thread.release_NOAUTO(state.ll_lock)
        def after():
            ll_thread.acquire_NOAUTO(state.ll_lock, True)
            ll_thread.gc_thread_run()

        class Cons:
            def __init__(self, head, tail):
                self.head = head
                self.tail = tail

        def bootstrap():
            ll_thread.gc_thread_start()
            state.xlist.append(Cons(123, Cons(456, None)))
            gc.collect()
            ll_thread.gc_thread_die()

        def new_thread():
            ll_thread.gc_thread_prepare()
            ident = ll_thread.start_new_thread(bootstrap, ())
            time.sleep(0.5)    # enough time to start, hopefully
            return ident

        def entry_point(argv):
            os.write(1, "hello world\n")
            state.xlist = []
            x2 = Cons(51, Cons(62, Cons(74, None)))
            # start 5 new threads
            state.ll_lock = ll_thread.allocate_ll_lock()
            after()
            invoke_around_extcall(before, after)
            ident1 = new_thread()
            ident2 = new_thread()
            #
            gc.collect()
            #
            ident3 = new_thread()
            ident4 = new_thread()
            ident5 = new_thread()
            # wait for the 5 threads to finish
            while True:
                gc.collect()
                if len(state.xlist) == 5:
                    break
                time.sleep(0.1)      # invokes before/after
            # check that the malloced structures were not overwritten
            assert x2.head == 51
            assert x2.tail.head == 62
            assert x2.tail.tail.head == 74
            assert x2.tail.tail.tail is None
            # check the structures produced by the threads
            for i in range(5):
                assert state.xlist[i].head == 123
                assert state.xlist[i].tail.head == 456
                assert state.xlist[i].tail.tail is None
                os.write(1, "%d ok\n" % (i+1))
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('')
        assert data.splitlines() == ['hello world',
                                     '1 ok',
                                     '2 ok',
                                     '3 ok',
                                     '4 ok',
                                     '5 ok']


    def test_thread_and_gc_with_fork(self):
        # This checks that memory allocated for the shadow stacks of the
        # other threads is really released when doing a fork() -- or at
        # least that the object referenced from stacks that are no longer
        # alive are really freed.
        import time, gc, os
        from pypy.module.thread import ll_thread
        from pypy.rlib.objectmodel import invoke_around_extcall
        if not hasattr(os, 'fork'):
            py.test.skip("requires fork()")

        class State:
            pass
        state = State()

        def before():
            ll_assert(not ll_thread.acquire_NOAUTO(state.ll_lock, False),
                      "lock not held!")
            ll_thread.release_NOAUTO(state.ll_lock)
        def after():
            ll_thread.acquire_NOAUTO(state.ll_lock, True)
            ll_thread.gc_thread_run()

        class Cons:
            def __init__(self, head, tail):
                self.head = head
                self.tail = tail

        class Stuff:
            def __del__(self):
                os.write(state.write_end, 'd')

        def allocate_stuff():
            s = Stuff()
            os.write(state.write_end, 'a')
            return s

        def run_in_thread():
            for i in range(10):
                state.xlist.append(Cons(123, Cons(456, None)))
                time.sleep(0.01)
            childpid = os.fork()
            return childpid

        def bootstrap():
            ll_thread.gc_thread_start()
            childpid = run_in_thread()
            gc.collect()        # collect both in the child and in the parent
            gc.collect()
            gc.collect()
            if childpid == 0:
                os.write(state.write_end, 'c')   # "I did not die!" from child
            else:
                os.write(state.write_end, 'p')   # "I did not die!" from parent
            ll_thread.gc_thread_die()

        def new_thread():
            ll_thread.gc_thread_prepare()
            ident = ll_thread.start_new_thread(bootstrap, ())
            time.sleep(0.5)    # enough time to start, hopefully
            return ident

        def start_all_threads():
            s = allocate_stuff()
            ident1 = new_thread()
            ident2 = new_thread()
            ident3 = new_thread()
            ident4 = new_thread()
            ident5 = new_thread()
            # wait for 4 more seconds, which should be plenty of time
            time.sleep(4)
            keepalive_until_here(s)

        def entry_point(argv):
            os.write(1, "hello world\n")
            state.xlist = []
            state.deleted = 0
            state.read_end, state.write_end = os.pipe()
            x2 = Cons(51, Cons(62, Cons(74, None)))
            # start 5 new threads
            state.ll_lock = ll_thread.allocate_ll_lock()
            after()
            invoke_around_extcall(before, after)
            start_all_threads()
            # force freeing
            gc.collect()
            gc.collect()
            gc.collect()
            # return everything that was written to the pipe so far,
            # followed by the final dot.
            os.write(state.write_end, '.')
            result = os.read(state.read_end, 256)
            os.write(1, "got: %s\n" % result)
            return 0

        t, cbuilder = self.compile(entry_point)
        data = cbuilder.cmdexec('')
        print repr(data)
        header, footer = data.splitlines()
        assert header == 'hello world'
        assert footer.startswith('got: ')
        result = footer[5:]
        # check that all 5 threads and 5 forked processes
        # finished successfully, that we did 1 allocation,
        # and that it was freed 6 times -- once in the parent
        # process and once in every child process.
        assert (result[-1] == '.'
                and result.count('c') == result.count('p') == 5
                and result.count('a') == 1
                and result.count('d') == 6)
