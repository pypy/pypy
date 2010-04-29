from pypy.module.cpyext.test.test_api import BaseApiTest

class TestFloatObject(BaseApiTest):
    def test_floatobject(self, space, api):
        assert space.unwrap(api.PyFloat_FromDouble(3.14)) == 3.14
        assert api.PyFloat_AsDouble(space.wrap(23.45)) == 23.45
        assert api.PyFloat_AS_DOUBLE(space.wrap(23.45)) == 23.45

        assert api.PyFloat_AsDouble(space.w_None) == -1
        api.PyErr_Clear()

    def test_coerce(self, space, api):
        assert space.type(api.PyNumber_Float(space.wrap(3))) is space.w_float

        class Coerce(object):
            def __float__(self):
                return 42.5
        assert space.eq_w(api.PyNumber_Float(space.wrap(Coerce())),
                          space.wrap(42.5))
