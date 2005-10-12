import autopath
from pypy.translator.asm.simulator import Machine
from pypy.objspace.flow.model import Constant
from pypy.translator.asm.infregmachine import Instruction

def test_insn_by_insn():
    machine=Machine(5,[0,1111,2222,3333])   # create an IRM with 5 registers to use

    assert machine.registers()==[None,None,None,None,None]   # check initialised.

    machine.op('LOAD',1,Constant(555))
    assert machine.registers()==[555,None,None,None,None]

    machine.op('LIA',2,Constant(0))  #argument 1 to register 2
    assert machine.registers()==[555,0,None,None,None]
    machine.op('LIA',3,Constant(2))  #argument 3 to register 3
    assert machine.registers()==[555,0,2222,None,None]

    machine.op('MOV',2,1)
    assert machine.registers()==[555,555,2222,None,None]

    machine.op('EXCH',3,2)
    assert machine.registers()==[555,2222,555,None,None]

    machine.op('int_add',4,2,1)
    assert machine.registers()==[555,2222,555,2222+555,None]

    try:
        machine.register(5)
    except AssertionError:
        pass
    else:
        assert False, "should not get here"

    machine=Machine(3,[])
    assert machine.creg()==None
    machine.LOAD(1,Constant(1))
    machine.LOAD(2,Constant(2))
    machine.int_gt(1,2)
    assert machine.creg()==False
    machine.int_gt(2,1)
    assert machine.creg()==True


def test_programs():
    assert Machine.RunProgram([])==None   #check our program returns None if no RETPYTHON !!!
    assert Machine.RunProgram([Instruction('LOAD',(1,Constant(23))),Instruction('RETPYTHON',(1,))])==23

    prog=[Instruction('LOAD', (1, Constant(100))),
          Instruction('J', ('label',)),
          Instruction('LOAD', (1, Constant(200))),
          'label',
          'label2',
          Instruction('RETPYTHON', (1,))]

    assert Machine.RunProgram(prog) == 100

    prog=[Instruction('LIA', (1, Constant(0))),
          Instruction('LIA', (2, Constant(1))),
          Instruction('LOAD', (3, Constant(77))),
          Instruction('int_gt', (1, 2)),
          Instruction('JT', ('label',)),
          Instruction('LIA', (3, Constant(2))),
          'label',
          Instruction('RETPYTHON', (3,))]
    
    assert Machine.RunProgram(prog, [1,2,3]) == 3
    assert Machine.RunProgram(prog, [2,1,3]) == 77

