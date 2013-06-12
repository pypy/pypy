class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('pyrolog',))

    def test_import(self):
        from pypy.module.pyrolog.glue.conversion import hello_world
        ok = hello_world()
        assert(ok)
