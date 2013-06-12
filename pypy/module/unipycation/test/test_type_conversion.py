import pypy.module.unipycation.conversion as conv

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    """
    def test_import(self):
        ok = conv.hello_world()
        assert(ok)
    """

    def test_int_p_of_int_w(self):
        int_w = self.space.newint(666)
        int_p = conv.int_p_of_int_w(self.space, int_w)

        unwrap1 = self.space.int_w(int_w)
        unwrap2 = int_p.num # no unwrap helper in pyrolog?

        ok = (unwrap1 == unwrap2)

        print("Expected %d, got %d" % (unwrap1, unwrap2))
        assert(ok)
