
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestUfuncs(BaseNumpyAppTest):
    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        from pypy.module.micronumpy import halffloat
        cls.w_halffloat = cls.space.wrap(halffloat)
        
    def test_bitconvert_exact(self):
        #from _numpypy import array, uint32
        # These test cases were created by 
        # numpy.float16(v).view(uint16)
        # numpy.float32(v).view(uint32)
        cases = [[0., 0, 0], [10, 1092616192, 18688], [-10, 3240099840, 51456], 
                 [10e3, 1176256512, 28898], [float('inf'), 2139095040, 31744], 
                 [-float('inf'), 4286578688, 64512]]
        for v, fbits, hbits in cases:
            # No 'view' in numpypy yet
            # fbits = array(v, dtype='float32').view(uint32)
            f = self.halffloat.floatbits_to_halfbits(fbits)
            assert [f, v] == [hbits, v]
            f = self.halffloat.halfbits_to_floatbits(hbits)
            assert [f, v] == [fbits, v]
    def test_bitconvert_inexact(self):
        cases = [[10.001, 1092617241, 1092616192, 18688],
                 [-10.001, 3240100889, 3240099840, 51456],
                 [22001.0, 1185669632, 1185669120, 30047],]
        for v, fexact, finexact, hbits in cases:
            f = self.halffloat.floatbits_to_halfbits(fexact)
            assert [f, v] == [hbits, v]
            f = self.halffloat.halfbits_to_floatbits(hbits)
            assert [f, v] == [finexact, v]

