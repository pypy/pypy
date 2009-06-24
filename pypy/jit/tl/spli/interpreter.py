from pypy.tool import stdlib_opcode as opcode
from pypy.jit.tl.spli.pycode import Code
from pypy.jit.tl.spli import objects
import dis

compare_ops = [
    "cmp_lt",   # "<"
    "cmp_le",   # "<="
    "cmp_eq",   # "=="
    "cmp_ne",   # "!="
    "cmp_gt",   # ">"
    "cmp_ge",   # ">="
    "cmp_in",
    "cmp_not_in",
    "cmp_is",
    "cmp_is_not",
    "cmp_exc_match",
]

def spli_run_from_cpython_code(co, args=[]):
    space = objects.DumbObjSpace()
    pyco = Code._from_code(space, co)
    print dis.dis(co)
    return run(pyco, args, space)

def run(pyco, args, space=None):
    if space is None:
        space = objects.DumbObjSpace()
    frame = SPLIFrame(pyco)
    for i, arg in enumerate(args):
        frame.locals[i] = space.wrap(arg)
    return frame.run()    

class BlockUnroller(Exception):
    pass

class Return(BlockUnroller):

    def __init__(self, value):
        self.value = value


class SPLIFrame(object):

    def __init__(self, code):
        self.code = code
        self.value_stack = [None] * code.co_stacksize
        self.locals = [None] * len(code.getvarnames())

    def run(self):
        self.stack_depth = 0
        try:
            self._dispatch_loop()
        except Return, ret:
            return ret.value

    def _dispatch_loop(self):
        code = self.code.co_code
        instr_index = 0
        while True:
            op = ord(code[instr_index])
            instr_index += 1
            if op >= opcode.HAVE_ARGUMENT:
                low = ord(code[instr_index])
                hi = ord(code[instr_index + 1])
                oparg = (hi << 8) | low
                instr_index += 2
            else:
                oparg = 0
            meth = getattr(self, opcode.opcode_method_names[op])
            instr_index = meth(oparg, instr_index)

    def push(self, value):
        self.value_stack[self.stack_depth] = value
        self.stack_depth += 1

    def pop(self):
        self.stack_depth -= 1
        val = self.value_stack[self.stack_depth]
        self.value_stack[self.stack_depth] = None
        return val

    def peek(self):
        return self.value_stack[self.stack_depth - 1]

    def POP_TOP(self, _, next_instr):
        self.pop()
        return next_instr

    def LOAD_FAST(self, name_index, next_instr):
        self.push(self.locals[name_index])
        return next_instr

    def STORE_FAST(self, name_index, next_instr):
        self.locals[name_index] = self.pop()
        return next_instr

    def RETURN_VALUE(self, _, next_instr):
        raise Return(self.pop())

    def LOAD_CONST(self, const_index, next_instr):
        self.push(self.code.co_consts_w[const_index])
        return next_instr

    def BINARY_ADD(self, _, next_instr):
        right = self.pop()
        left = self.pop()
        self.push(left.add(right))
        return next_instr

    def SETUP_LOOP(self, _, next_instr):
        return next_instr

    def POP_BLOCK(self, _, next_instr):
        return next_instr

    def JUMP_IF_FALSE(self, arg, next_instr):
        w_cond = self.peek()
        if not w_cond.is_true():
            next_instr += arg
        return next_instr

    def JUMP_ABSOLUTE(self, arg, next_instr):
        return arg

    def COMPARE_OP(self, arg, next_instr):
        right = self.pop()
        left = self.pop()
        self.push(getattr(left, compare_ops[arg])(right))
        return next_instr
