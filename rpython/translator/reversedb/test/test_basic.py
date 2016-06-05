import py
from rpython.translator.interactive import Translation


class TestBasic(object):

    def getcompiled(self, entry_point, argtypes, backendopt=True):
        t = Translation(entry_point, None, gc="boehm")
        t.config.translation.reversedb = True
        t.config.translation.rweakref = False
        if not backendopt:
            t.disable(["backendopt_lltype"])
        t.annotate()
        t.rtype()
        if t.backendopt:
            t.backendopt()
        t.compile_c()

        def run(*argv):
            stdout = t.driver.cbuilder.cmdexec(' '.join(argv))
            return stdout
        return run

    def test_simple(self):
        def main(argv):
            print argv[1:]
            return 0
        fn = self.getcompiled(main, [], backendopt=False)
        assert fn('abc d') == '[abc, d]\n'
