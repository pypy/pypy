
from pypy.module.micronumpy.test.test_base import BaseNumpyAppTest

class AppTestUfuncs(BaseNumpyAppTest):
    def setup_class(cls):
        BaseNumpyAppTest.setup_class.im_func(cls)
        from pypy.module.micronumpy import halffloat
        cls.w_halffloat = cls.space.wrap(halffloat)
        
    def test_bitconvert_exact_f(self):
        #from _numpypy import array, uint32 ## Do this when 'view' works
        # These test cases were created by 
        # numpy.float32(v).view(uint32)
        # numpy.float16(v).view(uint16)
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
            
    def test_bitconvert_inexact_f(self):
        # finexact is 
        # numpy.float32(numpy.float16(v)).view(uint32)
        cases = [[10.001, 1092617241, 1092616192, 18688],
                 [-10.001, 3240100889, 3240099840, 51456],
                 [22001.0, 1185669632, 1185669120, 30047],]
        for v, fexact, finexact, hbits in cases:
            f = self.halffloat.floatbits_to_halfbits(fexact)
            assert [f, v] == [hbits, v]
            f = self.halffloat.halfbits_to_floatbits(hbits)
            assert [f, v] == [finexact, v]

    def test_bitconvert_overunderflow_f(self):
        cases = [[67000.0, 1199758336, 2139095040, 31744],
                 [-67000.0, 3347241984, 4286578688, 64512],
                 [1e-08, 841731191, 0, 0], 
                 [-1e-08, 2989214839, 2147483648, 32768],
                ]
        for v, fexact, finexact, hbits in cases:
            f = self.halffloat.floatbits_to_halfbits(fexact)
            assert [f, v] == [hbits, v]
            f = self.halffloat.halfbits_to_floatbits(hbits)
            assert [f, v] == [finexact, v]

    def test_bitconvert_exact_d(self):
        #from _numpypy import array, uint32 ## Do this when 'view' works
        # These test cases were created by 
        # numpy.float64(v).view(uint64)
        # numpy.float16(v).view(uint16)
        cases =[[0, 0, 0], [10, 4621819117588971520, 18688], 
                [-10, 13845191154443747328, 51456], 
                [10000.0, 4666723172467343360, 28898], 
                [float('inf'), 9218868437227405312, 31744], 
                [-float('inf'), 18442240474082181120, 64512]]
        for v, dbits, hbits in cases:
            # No 'view' in numpypy yet
            # dbits = array(v, dtype='float64').view(uint64)
            h = self.halffloat.doublebits_to_halfbits(dbits)
            assert [h, v] == [hbits, v]
            d = self.halffloat.halfbits_to_doublebits(hbits)
            assert [d, v] == [dbits, v]

    def test_bitconvert_inexact_d(self):
        # finexact is 
        # numpy.float64(numpy.float16(v)).view(uint64)
        cases = [[10.001, 4621819680538924941, 4621819117588971520, 18688], 
                 [-10.001, 13845191717393700749, 13845191154443747328, 51456], 
                 [22001, 4671776802786508800, 4671776527908601856, 30047]]
        for v, fexact, finexact, hbits in cases:
            f = self.halffloat.doublebits_to_halfbits(fexact)
            assert [f, v] == [hbits, v]
            f = self.halffloat.halfbits_to_doublebits(hbits)
            assert [f, v] == [finexact, v]
