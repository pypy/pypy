import py
import operator
from pypy.jit.tl import interp
from pypy.jit.bytecode import *

#from pypy.rpython.l3interp import l3interp
#from pypy.rpython.l3interp import model
#from pypy.rpython.l3interp.model import Op
#from pypy.translator.c.test.test_genc import compile 
from pypy.translator.translator import TranslationContext
from pypy.annotation import policy

def translate(func, inputargs):
    t = TranslationContext()
    pol = policy.AnnotatorPolicy()
    pol.allow_someobjects = False
    t.buildannotator(policy=pol).build_types(func, inputargs)
    t.buildrtyper().specialize()

    from pypy.translator.tool.cbuild import skip_missing_compiler
    from pypy.translator.c import genc
    builder = genc.CExtModuleBuilder(t, func)
    builder.generate_source()
    skip_missing_compiler(builder.compile)
    builder.import_module()
    return builder.get_entry_point()  

def compile(insn):
    return ''.join([chr(i & 0xff) for i in insn])

# actual tests go here

def test_tl_push():
    assert interp(compile([PUSH, 16])) == 16

def test_tl_pop():
    assert interp( compile([PUSH,16, PUSH,42, PUSH,100, POP]) ) == 42

def test_tl_add():
    assert interp( compile([PUSH,42, PUSH,100, ADD]) ) == 142
    assert interp( compile([PUSH,16, PUSH,42, PUSH,100, ADD]) ) == 142

def test_tl_error():
    py.test.raises(IndexError, interp,compile([POP]))
    py.test.raises(IndexError, interp,compile([ADD]))
    py.test.raises(IndexError, interp,compile([PUSH,100, ADD]) )

def test_tl_invalid_codetype():
    py.test.raises(TypeError, interp,[INVALID])

def test_tl_invalid_bytecode():
    py.test.raises(RuntimeError, interp,compile([INVALID]))

def test_tl_translatable():
    code = compile([PUSH,42, PUSH,100, ADD])
    fn = translate(interp, [str])
    assert interp(code) == fn(code)

def test_swap():
    code = [PUSH,42, PUSH, 84]
    assert interp(compile(code)) == 84
    code.append(SWAP)
    assert interp(compile(code)) == 42
    code.append(POP)
    assert interp(compile(code)) == 84

def test_pick():
    values = [7, 8, 9]
    code = []
    for v in reversed(values):
        code.extend([PUSH, v])

    for i, v in enumerate(values):
        assert interp(compile(code + [PICK,i])) == v

def test_put():
    values = [1,2,7,-3]
    code = [PUSH,0] * len(values)
    for i, v in enumerate(values):
        code += [PUSH,v, PUT,i]

    for i, v in enumerate(values):
        assert interp(compile(code + [PICK,i])) == v

ops = [ (ADD, operator.add, ((2, 4), (1, 1), (-1, 1))),
        (SUB, operator.sub, ((2, 4), (4, 2), (1, 1))),
        (MUL, operator.mul, ((2, 4), (4, 2), (1, 1), (-1, 6), (0, 5))),
        (DIV, operator.div, ((2, 4), (4, 2), (1, 1), (-4, -2), (0, 9), (9, -3))),
        (EQ, operator.eq, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
        (NE, operator.ne, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
        (LT, operator.lt, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
        (LE, operator.le, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
        (GT, operator.gt, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
        (GE, operator.ge, ((0, 0), (0, 1), (1, 0), (1, 1), (-1, 0), (0, -1), (-1, -1), (1, -1),  (-1, 1))),
      ]

def test_ops():
      for insn, pyop, values in ops:
          for first, second in values:
              code = [PUSH, first, PUSH, second, insn]
              assert interp(compile(code)) == pyop(first, second)


def test_branch_forward():
    assert interp(compile([PUSH,1, PUSH,0, BR_COND,2, PUSH,-1])) == -1
    assert interp(compile([PUSH,1, PUSH,1, BR_COND,2, PUSH,-1])) == 1
    assert interp(compile([PUSH,1, PUSH,-1, BR_COND,2, PUSH,-1])) == 1

def test_branch_backwards():
    assert interp(compile([PUSH,0, PUSH,1, BR_COND,6, PUSH,-1, PUSH,3, BR_COND,4, PUSH,2, BR_COND,-10])) == -1

def test_branch0():
    assert interp(compile([PUSH,7, PUSH,1, BR_COND,0])) == 7

def test_exit():
    assert py.test.raises(IndexError, interp, compile([EXIT]))
    assert interp(compile([PUSH,7, EXIT, PUSH,5])) == 7

def test_rot():
    code = [PUSH,1, PUSH,2, PUSH,3, ROT,3] 
    assert interp(compile(code)) == 2
    assert interp(compile(code + [POP])) == 1
    assert interp(compile(code + [POP, POP])) == 3

    py.test.raises(IndexError, interp, compile([PUSH,1, PUSH,2, PUSH,3, ROT,4]))

def test_call_ret():
    assert py.test.raises(IndexError, interp, compile([RETURN]))
    assert interp(compile([PUSH,6, RETURN, PUSH,4, EXIT, PUSH,9])) == 9
    assert interp(compile([CALL,0])) == 2

    assert interp(compile([PUSH,1, CALL,5, PUSH,2, CALL,2, EXIT, RETURN, ROT,3, ADD, SWAP, RETURN])) == 3
