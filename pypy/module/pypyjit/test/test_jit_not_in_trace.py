
class AppTestJitNotInTrace(object):
    spaceconfig = dict(usemodules=('pypyjit',))

    def test_not_from_assembler(self):
        import pypyjit
        @pypyjit.not_from_assembler
        def f(x, y):
            return 42
        r = f(3, 4)
        assert r is None
