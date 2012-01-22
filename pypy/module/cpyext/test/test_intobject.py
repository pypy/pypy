from pypy.module.cpyext.test.test_api import BaseApiTest
from pypy.module.cpyext.test.test_cpyext import AppTestCpythonExtensionBase
import sys

class TestIntObject(BaseApiTest):
    def test_intobject(self, space, api):
        assert api.PyInt_Check(space.wrap(3))
        assert api.PyInt_Check(space.w_True)
        assert not api.PyInt_Check(space.wrap((1, 2, 3)))
        for i in [3, -5, -1, -sys.maxint, sys.maxint - 1]:
            x = api.PyInt_AsLong(space.wrap(i))
            y = api.PyInt_AS_LONG(space.wrap(i))
            assert x == i
            assert y == i
            w_x = api.PyInt_FromLong(x + 1)
            assert space.type(w_x) is space.w_int
            assert space.eq_w(w_x, space.wrap(i + 1))

        assert api.PyInt_AsLong(space.w_None) == -1
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()

        assert api.PyInt_AsLong(None) == -1
        assert api.PyErr_Occurred() is space.w_TypeError
        api.PyErr_Clear()

        assert api.PyInt_AsUnsignedLong(space.wrap(sys.maxint)) == sys.maxint
        assert api.PyInt_AsUnsignedLong(space.wrap(-5)) == sys.maxint * 2 + 1
        assert api.PyErr_Occurred() is space.w_ValueError
        api.PyErr_Clear()

        assert (api.PyInt_AsUnsignedLongMask(space.wrap(sys.maxint))
                == sys.maxint)
        assert (api.PyInt_AsUnsignedLongMask(space.wrap(10**30))
                == 10**30 % ((sys.maxint + 1) * 2))

    def test_coerce(self, space, api):
        class Coerce(object):
            def __int__(self):
                return 42
        assert api.PyInt_AsLong(space.wrap(Coerce())) == 42

class AppTestIntObject(AppTestCpythonExtensionBase):
    def test_fromstring(self):
        module = self.import_extension('foo', [
            ("from_string", "METH_NOARGS",
             """
                 return PyInt_FromString("1234", NULL, 16);
             """),
            ])
        assert module.from_string() == 0x1234
        assert type(module.from_string()) is int

    def test_size_t(self):
        module = self.import_extension('foo', [
            ("values", "METH_NOARGS",
             """
                 return Py_BuildValue("NNNN",
                     PyInt_FromSize_t(123),
                     PyInt_FromSize_t((size_t)-1),
                     PyInt_FromSsize_t(123),
                     PyInt_FromSsize_t((size_t)-1));
             """),
            ])
        values = module.values()
        types = [type(x) for x in values]
        assert types == [int, long, int, int]
        
