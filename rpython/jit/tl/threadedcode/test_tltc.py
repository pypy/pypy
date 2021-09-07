import py
from rpython.jit.tl.threadedcode import tltc
from rpython.jit.tl.threadedcode.tltc import \
    W_Object, W_IntObject, W_StringObject, W_Frame

def assemble(mylist):
    return ''.join([chr(x) for x in mylist])

def interp(mylist, w_arg):
    bytecode = assemble(mylist)
    return tltc.run(bytecode, w_arg)

class TestW_Frame:

    def test_add(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.ADD,
            tltc.EXIT
        ]
        res = interp(code, W_IntObject(123))
        assert res.intvalue == 123 + 123

    def test_sub(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.SUB,
            tltc.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 - 123

    def test_mul(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.MUL,
            tltc.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 * 123

    def test_div(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.DIV,
            tltc.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 / 123


    def test_jump(self):
        code = [
            tltc.JUMP, 3,
            tltc.ADD,
            tltc.EXIT
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234

    def test_call(self):
        code = [
            tltc.CALL, 3,
            tltc.EXIT,
            tltc.CONST_INT, 12,
            tltc.ADD,
            tltc.RET, 1
        ]
        res = interp(code, W_IntObject(34))
        assert res.intvalue == 34 + 12

    def test_simple_loop(self):
        code = [
            tltc.DUP,
            tltc.CONST_INT, 1,
            tltc.LT,
            tltc.JUMP_IF, 11,
            tltc.CONST_INT, 1,
            tltc.SUB,
            tltc.JUMP, 0,
            tltc.EXIT,
        ]
        res = interp(code, W_IntObject(100))
        assert res.intvalue == 0


from rpython.jit.metainterp.test.support import LLJitMixin

class TestLLType(LLJitMixin):
    def test_jit(self):
        code = [
            tltc.DUP,
            tltc.CONST_INT, 1,
            tltc.LT,
            tltc.JUMP_IF, 11,
            tltc.CONST_INT, 1,
            tltc.SUB,
            tltc.JUMP, 0,
            tltc.EXIT,
        ]
        def interp_w(intvalue):
            w_result = interp(code, W_IntObject(intvalue))
            assert isinstance(w_result, W_IntObject)
            return w_result.intvalue
        res = self.meta_interp(interp_w, [42], listops=True)
        pass
