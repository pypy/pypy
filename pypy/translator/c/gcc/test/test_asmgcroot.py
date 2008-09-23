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

    def getcompiled(self, func):
        def main(argv):
            try:
                res = func()
            except MemoryError:
                print 'Result: MemoryError'
            else:
                if isinstance(res, int):
                    print 'Result:', res
                else:
                    print 'Result: "%s"' % (res,)
            return 0
        from pypy.config.pypyoption import get_pypy_config
        config = get_pypy_config(translating=True)
        config.translation.gc = self.gcpolicy
        config.translation.gcrootfinder = "asmgcc"
        t = TranslationContext(config=config)
        self.t = t
        a = t.buildannotator()
        a.build_types(main, [s_list_of_strings])
        t.buildrtyper().specialize()
        t.checkgraphs()

        cbuilder = CStandaloneBuilder(t, main, config=config)
        c_source_filename = cbuilder.generate_source(
            defines = cbuilder.DEBUG_DEFINES)
        self.patch_makefile(cbuilder.targetdir)
        if conftest.option.view:
            t.view()
        exe_name = cbuilder.compile()

        def run():
            lines = []
            print >> sys.stderr, 'RUN: starting', exe_name
            g = os.popen("'%s'" % (exe_name,), 'r')
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

    def patch_makefile(self, targetdir):
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


class TestAsmGCRootWithSemiSpaceGC(AbstractTestAsmGCRoot,
                                   test_newgc.TestSemiSpaceGC):
    pass
    # for the individual tests see
    # ====> ../../test/test_newgc.py

    def test_callback_with_collect(self):
        py.test.skip("in-progress")
