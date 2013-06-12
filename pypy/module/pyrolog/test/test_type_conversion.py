import pypy.module.pyrolog.glue.conversion as conv

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('pyrolog',))

    def test_import(self):
        ok = conv.hello_world()
        assert(ok)

    def test_int_p_of_int_w(self):
        int_w = space.int_w(666)
        int_p = conv.int_p_of_int_w(int_w)
        ok = (str(int_w) == str(int_p))
        assert(ok)
