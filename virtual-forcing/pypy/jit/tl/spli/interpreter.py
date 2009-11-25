import os
from pypy.tool import stdlib_opcode as opcode
from pypy.jit.tl.spli import objects, pycode
from pypy.tool.stdlib_opcode import unrolling_opcode_descs
from pypy.tool.stdlib_opcode import opcode_method_names
from pypy.rlib.unroll import unrolling_iterable
from pypy.rlib.jit import JitDriver, hint, dont_look_inside
from pypy.rlib.objectmodel import we_are_translated


compare_ops = [
    "cmp_lt",   # "<"
    "cmp_le",   # "<="
    "cmp_eq",   # "=="
    "cmp_ne",   # "!="
    "cmp_gt",   # ">"
    "cmp_ge",   # ">="
#    "cmp_in",
#    "cmp_not_in",
#    "cmp_is",
#    "cmp_is_not",
#    "cmp_exc_match",
]
unrolling_compare_dispatch_table = unrolling_iterable(
    enumerate(compare_ops))

jitdriver = JitDriver(greens = ['code', 'instr_index'],
                      reds = ['frame'],
                      virtualizables = ['frame'])


class BlockUnroller(Exception):
    pass

class Return(BlockUnroller):

    def __init__(self, value):
        self.value = value

class MissingOpcode(Exception):
    pass

class SPLIFrame(object):

    _virtualizable2_ = ['value_stack[*]', 'locals[*]', 'stack_depth']

    @dont_look_inside
    def __init__(self, code, locs=None, globs=None):
        self.code = code
        self.value_stack = [None] * code.co_stacksize
        self.locals = [None] * code.co_nlocals
        if locs is not None:
            self.locals_dict = locs
        else:
            self.locals_dict = {}
        if globs is not None:
            self.globs = globs
        else:
            self.globs = {}
        self.stack_depth = 0

    def set_args(self, args):
        for i in range(len(args)):
            self.locals[i] = args[i]

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
            jitdriver.jit_merge_point(code=code, instr_index=instr_index,
                                      frame=self)
            self.stack_depth = hint(self.stack_depth, promote=True)
            op = ord(code[instr_index])
            instr_index += 1
            if op >= opcode.HAVE_ARGUMENT:
                low = ord(code[instr_index])
                hi = ord(code[instr_index + 1])
                oparg = (hi << 8) | low
                instr_index += 2
            else:
                oparg = 0
            if we_are_translated():
                for opdesc in unrolling_opcode_descs:
                    if op == opdesc.index:
                        meth = getattr(self, opdesc.methodname)
                        instr_index = meth(oparg, instr_index, code)
                        break
                else:
                    raise MissingOpcode(op)
            else:
                meth = getattr(self, opcode_method_names[op])
                instr_index = meth(oparg, instr_index, code)

    def push(self, value):
        self.value_stack[self.stack_depth] = value
        self.stack_depth += 1

    def pop(self):
        self.stack_depth -= 1
        val = self.value_stack[self.stack_depth]
        self.value_stack[self.stack_depth] = None
        return val

    def pop_many(self, n):
        return [self.pop() for i in range(n)]

    def peek(self):
        return self.value_stack[self.stack_depth - 1]

    def POP_TOP(self, _, next_instr, code):
        self.pop()
        return next_instr

    def LOAD_FAST(self, name_index, next_instr, code):
        self.push(self.locals[name_index])
        return next_instr

    def STORE_FAST(self, name_index, next_instr, code):
        self.locals[name_index] = self.pop()
        return next_instr

    def LOAD_NAME(self, name_index, next_instr, code):
        name = self.code.co_names[name_index]
        self.push(self.locals_dict[name])
        return next_instr

    def STORE_NAME(self, name_index, next_instr, code):
        name = self.code.co_names[name_index]
        self.locals_dict[name] = self.pop()
        return next_instr

    def LOAD_GLOBAL(self, name_index, next_instr, code):
        name = self.code.co_names[name_index]
        self.push(self.globs[name])
        return next_instr

    def STORE_GLOBAL(self, name_index, next_instr, code):
        name = self.code.co_names[name_index]
        self.globs[name] = self.pop()
        return next_instr

    def RETURN_VALUE(self, _, next_instr, code):
        raise Return(self.pop())

    def LOAD_CONST(self, const_index, next_instr, code):
        self.push(self.code.co_consts_w[const_index])
        return next_instr

    def BINARY_ADD(self, _, next_instr, code):
        right = self.pop()
        left = self.pop()
        self.push(left.add(right))
        return next_instr

    def BINARY_SUBTRACT(self, _, next_instr, code):
        right = self.pop()
        left = self.pop()
        self.push(left.sub(right))
        return next_instr

    def BINARY_AND(self, _, next_instr, code):
        right = self.pop()
        left = self.pop()
        self.push(left.and_(right))
        return next_instr        

    def SETUP_LOOP(self, _, next_instr, code):
        return next_instr

    def POP_BLOCK(self, _, next_instr, code):
        return next_instr

    def JUMP_IF_FALSE(self, arg, next_instr, code):
        w_cond = self.peek()
        if not w_cond.is_true():
            next_instr += arg
        return next_instr

    def JUMP_FORWARD(self, arg, next_instr, code):
        return next_instr + arg

    def JUMP_ABSOLUTE(self, arg, next_instr, code):
        jitdriver.can_enter_jit(frame=self, code=code, instr_index=arg)
        return arg

    def COMPARE_OP(self, arg, next_instr, code):
        right = self.pop()
        left = self.pop()
        for num, name in unrolling_compare_dispatch_table:
            if num == arg:
                self.push(getattr(left, name)(right))
        return next_instr

    def MAKE_FUNCTION(self, _, next_instr, code):
        func_code = self.pop().as_interp_class(pycode.Code)
        func = objects.Function(func_code, self.globs)
        self.push(func)
        return next_instr

    def CALL_FUNCTION(self, arg_count, next_instr, code):
        args = self.pop_many(arg_count)
        func = self.pop()
        self.push(func.call(args))
        return next_instr

    def PRINT_ITEM(self, _, next_instr, code):
        value = self.pop().repr().as_str()
        os.write(1, value)
        return next_instr

    def PRINT_NEWLINE(self, _, next_instr, code):
        os.write(1, '\n')
        return next_instr


items = []
for item in unrolling_opcode_descs._items:
    if getattr(SPLIFrame, item.methodname, None) is not None:
        items.append(item)
unrolling_opcode_descs = unrolling_iterable(items)
