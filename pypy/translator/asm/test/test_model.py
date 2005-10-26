from pypy.translator.asm.model import *
import py

def test_simple():
    prog = [LOAD_IMMEDIATE(0, 1),
            RETPYTHON(0)]
    machine = Machine(prog)
    assert machine.execute() == 1

def test_args():
    prog = [LOAD_ARGUMENT(0, 0),
            RETPYTHON(0)]
    machine = Machine(prog)

    for i in range(20):
        assert machine.execute(i) == i
    
def test_jump():
    prog = [LOAD_IMMEDIATE(0, 0),
            JUMP("branch"),
            LOAD_IMMEDIATE(0, 1),
            Label("branch"),
            RETPYTHON(0)]

    assert Machine(prog).execute() == 0


def test_cond_jump():
    prog = [LOAD_ARGUMENT(0, 0),
            LOAD_ARGUMENT(1, 1),
            LOAD_ARGUMENT(2, 2),
            JUMP_IF_FALSE(0, "branch"),
            RETPYTHON(1),
            Label("branch"),
            RETPYTHON(2)]

    assert Machine(prog).execute(True, 1, 2) == 1
    assert Machine(prog).execute(False, 1, 2) == 2

    prog = [LOAD_ARGUMENT(0, 0),
            LOAD_ARGUMENT(1, 1),
            LOAD_ARGUMENT(2, 2),
            JUMP_IF_TRUE(0, "branch"),
            RETPYTHON(1),
            Label("branch"),
            RETPYTHON(2)]

    assert Machine(prog).execute(True, 1, 2) == 2
    assert Machine(prog).execute(False, 1, 2) == 1

def test_llinstruction():
    prog = [LOAD_IMMEDIATE(0, 1),
            LOAD_IMMEDIATE(1, 2),
            LLInstruction('int_add', 0, 0, 1),
            RETPYTHON(0)]

    assert Machine(prog).execute() == 3

def test_mov():
    prog = [LOAD_IMMEDIATE(0, 0),
            LOAD_IMMEDIATE(1, 1),
            MOVE(0, 1),
            RETPYTHON(0)]

    assert Machine(prog).execute() == 1

def test_stack():
    prog = [LOAD_ARGUMENT(0, 0),
            STORE_STACK(0, 0),
            LOAD_STACK(1, 0),
            RETPYTHON(1)]

    assert Machine(prog).execute(1) == 1
    assert Machine(prog).execute(2) == 2

def test_errors():
    # these should fail, it's not that relavent how...
    py.test.raises(Exception, Machine([]).execute)
    py.test.raises(Exception, Machine([RETPYTHON(0)]).execute)

