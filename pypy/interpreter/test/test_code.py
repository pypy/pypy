from pypy.interpreter.pycode import PyCode
from pypy.interpreter import gateway
import py

class TestCode:
    def test_code_eq_corner_cases(self):
        space = self.space
        def make_code_with_const(w_obj):
            return PyCode(space, 0, 0, 0, 0, 1, 0, '', [w_obj], [], [], '', '', '', 0, '', [], [], False)
        def cmp_code_consts(w_obj1, w_obj2):
            w_code1 = make_code_with_const(w_obj1)
            w_code2 = make_code_with_const(w_obj2)

            # code objects in co_consts are compared by identity
            # (we never share them in the bytecode compiler, it happens
            # extremely rarely and is not useful anyway)

            res1 = space.is_true(space.eq(w_code1, w_code2))
            res2 = space.is_true(space.eq(w_code2, w_code1))
            if res1:
                # if the code objects are equal, the hash should be the same
                h1 = space.int_w(w_code1.descr_code__hash__())
                h2 = space.int_w(w_code2.descr_code__hash__())
                assert h1 == h2

            # check reflexivity
            assert res1 == res2


            # wrapping as code doesn't change the result
            w_codecode1 = make_code_with_const(w_code1)
            w_codecode2 = make_code_with_const(w_code2)
            assert space.is_true(space.eq(w_codecode1, w_codecode2)) == res1

            # check that tupleization doesn't change the result
            if not space.isinstance_w(w_obj1, space.w_tuple):
                res3 = cmp_code_consts(space.newtuple([space.w_None, w_obj1]),
                                       space.newtuple([space.w_None, w_obj2]))
                assert res3 == res1
            return res1

        assert cmp_code_consts(space.w_None, space.w_None)

        # floats
        assert not cmp_code_consts(space.newfloat(0.0), space.newfloat(-0.0))
        assert cmp_code_consts(space.newfloat(float('nan')), space.newfloat(float('nan')))

        # complex
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(-0.0, 0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, 0.0), space.newcomplex(-0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(-0.0, 0.0), space.newcomplex(0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(-0.0, 0.0), space.newcomplex(-0.0, -0.0))
        assert not cmp_code_consts(space.newcomplex(0.0, -0.0), space.newcomplex(-0.0, -0.0))

        # code objects: we compare them by identity, PyPy doesn't share them ever
