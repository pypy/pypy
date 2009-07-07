import py
from pypy.jit.tl import tla

def test_stack():
    f = tla.Frame('')
    f.push(1)
    f.push(2)
    f.push(3)
    assert f.pop() == 3
    assert f.pop() == 2
    assert f.pop() == 1
    py.test.raises(AssertionError, f.pop)


def test_W_IntObject():
    w_a = tla.W_IntObject(0)
    w_b = tla.W_IntObject(10)
    w_c = tla.W_IntObject(32)
    assert not w_a.is_true()
    assert w_b.is_true()
    assert w_c.is_true()
    assert w_b.add(w_c).intvalue == 42


def assemble(mylist):
    return ''.join([chr(x) for x in mylist])

def interp(mylist):
    bytecode = assemble(mylist)
    f = tla.Frame(bytecode)
    return f.interp()

def test_interp():
    bytecode = [
        tla.CONST_INT, 42,
        tla.RETURN
        ]
    assert interp(bytecode).intvalue == 42

