import unittest, sys
sys.path.append('..')

import extmodule

class EmptyBM(extmodule.BuiltinModule):
    __pythonname__ = 'empty_bm'

class wrapper(object):
    def __init__(self, wrapped):
        self.wrapped = wrapped
def is_wrapped(obj):
    return isinstance(obj, wrapper)
import new
class dummyspace(object):
    w_None = wrapper(None)
    def wrap(self, obj):
        return wrapper(obj)
    def unwrap(self, obj):
        return obj.wrapped
    def newmodule(self, name):
        return self.wrap(new.module(self.unwrap(name)))
    def newfunction(self, code, w_something, somethingelse):


class TestBuiltinModule(unittest.TestCase):

    def setUp(self):
        self.space = dummyspace()

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
