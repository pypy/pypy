import unittest, sys
import testsupport
from pypy.interpreter import unittest_w

# need pypy.module.builtin first to make other imports work (???)
from pypy.module import builtin

from pypy.interpreter import extmodule
from pypy.objspace import trivial

class EmptyBM(extmodule.BuiltinModule):
    __pythonname__ = 'empty_bm'

class TestBuiltinModule(unittest_w.TestCase_w):

    def setUp(self):
        self.space = trivial.TrivialObjSpace()

    def tearDown(self):
        pass

    def test_empty(self):
        bm = EmptyBM(self.space)
        w_bm = bm.wrap_me()
        modobj = self.space.unwrap(w_bm)
        bmd = modobj.__dict__
        bmd_kys = bmd.keys()
        bmd_kys.sort()
        self.assertEqual(bmd_kys, ['__doc__','__name__'])
        self.assertEqual(bmd['__doc__'], EmptyBM.__doc__)
        self.assertEqual(bmd['__name__'], EmptyBM.__pythonname__)

if __name__ == '__main__':
    unittest.main()
