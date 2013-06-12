import pypy.module.unipycation.conversion as conv

class TestTypeConversion(object):
    spaceconfig = dict(usemodules=('unipycation',))

    def test_int_p_of_int_w(self):
        int_w = self.space.newint(666)
        int_p = conv.int_p_of_int_w(self.space, int_w)

        unwrap1 = self.space.int_w(int_w)
        unwrap2 = int_p.num

        assert unwrap1 == unwrap2

    def test_float_p_of_float_w(self):
        float_w = self.space.newfloat(678.666)
        float_p = conv.float_p_of_float_w(self.space, float_w)

        unwrap1 = self.space.float_w(float_w)
        unwrap2 = float_p.floatval

        assert unwrap1 == unwrap2

    # corner case: test -0.0 converts properly
    def test_float_p_of_float_w_2(self):
        float_w = self.space.newfloat(-0.0)
        float_p = conv.float_p_of_float_w(self.space, float_w)

        unwrap1 = self.space.float_w(float_w)
        unwrap2 = float_p.floatval

        assert unwrap1 == unwrap2
