import py
import sys, os
from pypy.translator.c.test import test_newgc
from pypy.translator.translator import TranslationContext
from pypy.translator.c.genc import CStandaloneBuilder
from pypy.annotation.listdef import s_list_of_strings
from pypy import conftest

class AbstractTestAsmGCRoot:
    # the asmgcroot gc transformer doesn't generate gc_reload_possibly_moved
    # instructions:
    should_be_moving = False

    @classmethod
    def make_config(cls):
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = cls.gcpolicy
        config.translation.gcrootfinder = "asmgcc"
        return config

    @classmethod
    def _makefunc_str_int(cls, func):
        def main(argv):
            arg0 = argv[1]
            arg1 = int(argv[2])
            try:
                res = func(arg0, arg1)
            except MemoryError:
                print 'Result: MemoryError'
            else:
                print 'Result: "%s"' % (res,)
            return 0
        config = cls.make_config()
        t = TranslationContext(config=config)
        a = t.buildannotator()
        a.build_types(main, [s_list_of_strings])
        t.buildrtyper().specialize()
        t.checkgraphs()

        cbuilder = CStandaloneBuilder(t, main, config=config)
        c_source_filename = cbuilder.generate_source(
            defines = cbuilder.DEBUG_DEFINES)
        cls._patch_makefile(cbuilder.targetdir)
        if conftest.option.view:
            t.view()
        exe_name = cbuilder.compile()

        def run(arg0, arg1):
            lines = []
            print >> sys.stderr, 'RUN: starting', exe_name, arg0, arg1
            if sys.platform == 'win32':
                redirect = ' 2> NUL'
            else:
                redirect = ''
            g = os.popen('"%s" %s %d%s' % (exe_name, arg0, arg1, redirect), 'r')
            for line in g:
                print >> sys.stderr, 'RUN:', line.rstrip()
                lines.append(line)
            g.close()
            if not lines:
                py.test.fail("no output from subprocess")
            if not lines[-1].startswith('Result:'):
                py.test.fail("unexpected output from subprocess")
            result = lines[-1][len('Result:'):].strip()
            if result == 'MemoryError':
                raise MemoryError("subprocess got an RPython MemoryError")
            if result.startswith('"') and result.endswith('"'):
                return result[1:-1]
            else:
                return int(result)
        return run

    @classmethod
    def _patch_makefile(cls, targetdir):
        # for testing, patch the Makefile to add the -r option to
        # trackgcroot.py.
        makefile = targetdir.join('Makefile')
        f = makefile.open()
        lines = f.readlines()
        f.close()
        found = False
        for i in range(len(lines)):
            if 'trackgcroot.py' in lines[i]:
                lines[i] = lines[i].replace('trackgcroot.py',
                                            'trackgcroot.py -r')
                found = True
        assert found
        f = makefile.open('w')
        f.writelines(lines)
        f.close()

    if sys.platform == 'win32':
        def test_callback_with_collect(self):
            py.test.skip("No libffi yet with mingw32")

        def define_callback_with_collect(cls):
            return lambda: 0

class TestAsmGCRootWithSemiSpaceGC(AbstractTestAsmGCRoot,
                                   test_newgc.TestSemiSpaceGC):
    # for the individual tests see
    # ====> ../../test/test_newgc.py

    def define_large_function(cls):
        class A(object):
            def __init__(self):
                self.x = 0
        d = dict(A=A)
        exec ("def g(a):\n" +
              "    a.x += 1\n" * 1000 +
              "    return A()\n"
              ) in d
        g = d['g']
        def f():
            a = A()
            g(a)
            return a.x
        return f

    def test_large_function(self):        
        res = self.run('large_function')
        assert res == 1000

    def define_callback_simple(cls):
        import gc
        from pypy.rpython.lltypesystem import lltype, rffi
        from pypy.rpython.annlowlevel import llhelper
        from pypy.translator.tool.cbuild import ExternalCompilationInfo

        c_source = py.code.Source("""
        int mystuff(int(*cb)(int, int))
        {
            return cb(40, 2) + cb(3, 4);
        }
        """)
        eci = ExternalCompilationInfo(separate_module_sources=[c_source])
        S = lltype.GcStruct('S', ('x', lltype.Signed))
        CALLBACK = lltype.FuncType([lltype.Signed, lltype.Signed],
                                   lltype.Signed)
        z = rffi.llexternal('mystuff', [lltype.Ptr(CALLBACK)], lltype.Signed,
                            compilation_info=eci)

        def mycallback(a, b):
            gc.collect()
            return a + b

        def f():
            p = lltype.malloc(S)
            p.x = 100
            result = z(mycallback)
            return result * p.x

        return f


    def test_callback_simple(self):
        res = self.run('callback_simple')
        assert res == 4900


class TestAsmGCRootWithSemiSpaceGC_Mingw32(TestAsmGCRootWithSemiSpaceGC):
    # for the individual tests see
    # ====> ../../test/test_newgc.py

    @classmethod
    def setup_class(cls):
        if sys.platform != 'win32':
            py.test.skip("mingw32 specific test")
        if not ('mingw' in os.popen('gcc --version').read() and
                'GNU' in os.popen('make --version').read()):
            py.test.skip("mingw32 and MSYS are required for this test")

        test_newgc.TestSemiSpaceGC.setup_class.im_func(cls)

    @classmethod
    def make_config(cls):
        config = TestAsmGCRootWithSemiSpaceGC.make_config()
        config.translation.cc = 'mingw32'
        return config


    def test_callback_with_collect(self):
        py.test.skip("No libffi yet with mingw32")

    def define_callback_with_collect(cls):
        return lambda: 0

class TestAsmGCRootWithHybridTagged(AbstractTestAsmGCRoot,
                                    test_newgc.TestHybridTaggedPointers):
    pass
