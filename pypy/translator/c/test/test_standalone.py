import py
import sys, os, re

from pypy.rlib.rarithmetic import r_longlong
from pypy.translator.translator import TranslationContext
from pypy.translator.backendopt import all
from pypy.translator.c.genc import CStandaloneBuilder, ExternalCompilationInfo
from pypy.annotation.listdef import s_list_of_strings
from pypy.tool.udir import udir
from pypy.tool.autopath import pypydir


class TestStandalone(object):
    config = None
    
    def test_hello_world(self):
        def entry_point(argv):
            os.write(1, "hello world\n")
            argv = argv[1:]
            os.write(1, "argument count: " + str(len(argv)) + "\n")
            for s in argv:
                os.write(1, "   '" + str(s) + "'\n")
            return 0

        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source()
        cbuilder.compile()
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

        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source()
        cbuilder.compile()
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

        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source()
        cbuilder.compile()
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
        t = Translation(entry_point, backend='c', standalone=True, profopt="")
        # no counters
        t.backendopt()
        exe = t.compile()
        out = py.process.cmdexec("%s 500" % exe)
        assert int(out) == 500*501/2
        t = Translation(entry_point, backend='c', standalone=True, profopt="",
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

            t = TranslationContext(self.config)
            t.buildannotator().build_types(entry_point, [s_list_of_strings])
            t.buildrtyper().specialize()

            cbuilder = CStandaloneBuilder(t, entry_point, t.config)
            cbuilder.generate_source()
            cbuilder.compile()


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
        from pypy.module.posix.test.test_posix2 import need_sparse_files
        need_sparse_files()
        filename = str(udir.join('test_standalone_largefile'))
        r4800000000 = r_longlong(4800000000L)
        def entry_point(argv):
            fd = os.open(filename, os.O_RDWR | os.O_CREAT, 0644)
            os.lseek(fd, r4800000000, 0)
            os.write(fd, "$")
            newpos = os.lseek(fd, 0, 1)
            if newpos == r4800000000 + 1:
                print "OK"
            else:
                print "BAD POS"
            os.close(fd)
            return 0
        t = TranslationContext(self.config)
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()
        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source()
        cbuilder.compile()
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
            LL_strtod_formatd("%5f", 12.3);
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

class TestMaemo(TestStandalone):
    def setup_class(cls):
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
    def test_stack_size(self):
        import time
        from pypy.module.thread import ll_thread

        class State:
            pass
        state = State()

        def recurse(n):
            if n > 0:
                return recurse(n-1)+1
            else:
                state.ll_lock.release()
                time.sleep(0.2)
                state.ll_lock.acquire(True)
                return 0

        def bootstrap():
            # recurse a lot, like 2500 times
            state.ll_lock.acquire(True)
            recurse(2500)
            state.count += 1
            state.ll_lock.release()

        def entry_point(argv):
            os.write(1, "hello world\n")
            error = ll_thread.set_stacksize(int(argv[1]))
            assert error == 0
            # malloc a bit
            s1 = State(); s2 = State(); s3 = State()
            s1.x = 0x11111111; s2.x = 0x22222222; s3.x = 0x33333333
            # start 3 new threads
            state.ll_lock = ll_thread.Lock(ll_thread.allocate_ll_lock())
            state.count = 0
            ident1 = ll_thread.start_new_thread(bootstrap, ())
            ident2 = ll_thread.start_new_thread(bootstrap, ())
            ident3 = ll_thread.start_new_thread(bootstrap, ())
            # wait for the 3 threads to finish
            while True:
                state.ll_lock.acquire(True)
                if state.count == 3:
                    break
                state.ll_lock.release()
                time.sleep(0.1)
            # check that the malloced structures were not overwritten
            assert s1.x == 0x11111111
            assert s2.x == 0x22222222
            assert s3.x == 0x33333333
            os.write(1, "done\n")
            return 0

        t = TranslationContext()
        t.buildannotator().build_types(entry_point, [s_list_of_strings])
        t.buildrtyper().specialize()

        cbuilder = CStandaloneBuilder(t, entry_point, t.config)
        cbuilder.generate_source()
        cbuilder.compile()

        # recursing should crash with only 32 KB of stack,
        # and it should eventually work with more stack
        for test_kb in [32, 128, 512, 1024, 2048, 4096, 8192, 16384]:
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
