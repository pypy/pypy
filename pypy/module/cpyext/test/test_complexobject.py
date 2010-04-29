from pypy.module.cpyext.test.test_api import BaseApiTest

class TestComplexObject(BaseApiTest):
    def test_complexobject(self, space, api):
        w_value = api.PyComplex_FromDoubles(1.2, 3.4)
        assert space.unwrap(w_value) == 1.2+3.4j
        assert api.PyComplex_RealAsDouble(w_value) == 1.2
        assert api.PyComplex_ImagAsDouble(w_value) == 3.4

        assert api.PyComplex_RealAsDouble(space.wrap(42)) == 42
        assert api.PyComplex_RealAsDouble(space.wrap(1.5)) == 1.5
        assert api.PyComplex_ImagAsDouble(space.wrap(1.5)) == 0.0

        # cpython accepts anything for PyComplex_ImagAsDouble
        assert api.PyComplex_ImagAsDouble(space.w_None) == 0.0
        assert not api.PyErr_Occurred()
        assert api.PyComplex_RealAsDouble(space.w_None) == -1.0
        assert api.PyErr_Occurred()
        api.PyErr_Clear()
