from pypy.interpreter import pycode
from pypy.tool import stdlib_opcode as opcode
from pypy.jit.tl.spli import objects


def spli_run_from_cpython_code(co):
    pyco = pycode.PyCode._from_code(objects.DumbObjSpace(), co)
    return SPLIFrame(pyco).run()


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
            res = meth(oparg)
            if res is not None:
                instr_index = res

    def push(self, value):
        self.value_stack[self.stack_depth] = value
        self.stack_depth += 1

    def pop(self):
        self.stack_depth -= 1
        val = self.value_stack[self.stack_depth]
        return val

    def LOAD_FAST(self, name_index):
        self.push(self.locals[name_index])

    def STORE_FAST(self, name_index):
        self.locals[name_index] = self.pop()

    def RETURN_VALUE(self, _):
        raise Return(self.pop())

    def LOAD_CONST(self, const_index):
        self.push(self.code.co_consts_w[const_index])

    def BINARY_ADD(self, _):
        right = self.pop()
        left = self.pop()
        self.push(left.add(right))
