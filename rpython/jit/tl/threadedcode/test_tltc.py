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
            tltc.RETURN
        ]
        res = interp(code, W_IntObject(123))
        assert res.intvalue == 123 + 123

    def test_sub(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.SUB,
            tltc.RETURN
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 - 123

    def test_mul(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.MUL,
            tltc.RETURN
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 * 123

    def test_div(self):
        code = [
            tltc.CONST_INT, 123,
            tltc.DIV,
            tltc.RETURN
        ]
        res = interp(code, W_IntObject(234))
        assert res.intvalue == 234 / 123
