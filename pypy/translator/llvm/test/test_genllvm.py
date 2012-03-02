from pypy.translator.interactive import Translation


def compile(func, argtypes=None, gc=False):
    translation = Translation(func, argtypes, backend='llvm', verbose=False)
    translation.disable(['backendopt_lltype'])
    translation.config.translation.backendopt.none = True
    if gc:
        translation.config.translation.gctransformer = 'framework'
        translation.config.translation.gc = 'minimark'
    else:
        translation.config.translation.gctransformer = 'none'
        translation.config.translation.gc = 'none'

    translation.annotate()
    return translation.compile_llvm()


class TestSimple(object):
    def test_pass(self):
        def f():
            pass

        fc = compile(f)
        assert fc() == 0

    def test_return(self):
        def f():
            return 42

        fc = compile(f)
        assert fc() == 42

    def test_argument(self):
        def f(echo):
            return echo

        fc = compile(f, [int])
        assert fc(123) == 123

    def test_add_int(self):
        def f(i):
            return i + 1

        fc = compile(f, [int])
        assert fc(2) == 3
        assert fc(3) == 4

    def test_call(self):
        def g():
            return 11
        def f():
            return g()

        fc = compile(f)
        assert fc() == 11

    def test_bool(self):
        def f(b):
            return not b

        fc = compile(f, [bool])
        assert fc(True) == False
        assert fc(False) == True


class TestGarbageCollected(object):
    def test_struct(self):
        class C(object):
            pass

        def f(i):
            c = C()
            c.i = i
            return c.i

        fc = compile(f, [int], gc=True)
        assert fc(33) == 33
