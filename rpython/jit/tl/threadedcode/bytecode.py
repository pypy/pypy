bytecodes = []
hasarg = []

def define_op(name, has_arg=False):
    globals()[name] = len(bytecodes)
    bytecodes.append(name)
    hasarg.append(has_arg)

_bytecodes_has_args = [
    ('NOP', 0),
    ('CONST_INT', 1),
    ('CONST_NEG_INT', 1),
    ('CONST_FLOAT', 9),
    ('CONST_NEG_FLOAT', 9),
    ('CONST_N', 4),
    ('CONST_NEG_N', 4),
    ('DUP', 0),
    ('DUPN', 1),
    ('POP', 0),
    ('POP1', 0),
    ('LT', 0),
    ('GT', 0),
    ('EQ', 0),
    ('ADD', 0),
    ('SUB', 0),
    ('MUL', 0),
    ('DIV', 0),
    ('MOD', 0),
    ('EXIT', 0),
    ('JUMP', 1),
    ('JUMP_N', 4),
    ('JUMP_IF', 1),
    ('JUMP_IF_N', 4),
    ('CALL', 2),
    ('CALL_N', 4),
    ('CALL_ASSEMBLER', 2),
    ('CALL_TIER2', 2),
    ('CALL_TIER0', 2),
    ('RET', 1),
    ('NEWSTR', 1),
    ('FRAME_RESET', 3),
    ('PRINT', 0),
    ('LOAD', 0),
    ('STORE', 0),
    ('BUILD_LIST', 0),
    ('RAND_INT', 4),
    ('FLOAT_TO_INT', 0),
    ('INT_TO_FLOAT', 0),
    ('ABS_FLOAT', 1),
    ('SIN', 0),
    ('COS', 0),
    ('SQRT', 0)
]

for bytecode, has_arg in _bytecodes_has_args:
    define_op(bytecode, has_arg)

class CompilerContext(object):
    def __init__(self):
        self.data = []
        self.stack = []
        self.names_to_numbers = {}
        self.functions = {}

    def register_function(self, pos, f):
        self.functions[pos] = f

    def register_constant(self, val):
        self.stack.append(val)
        return len(self.stack) - 1

    def register_assignment(self, var, val):
        self.names_to_numbers[var] = val
        self.stack.append(val)
        return len(self.stack) - 1

    def emit(self, bc, arg=0):
        raise NotImplementedError

    def create_bytecode(self):
        raise NotImplementedError

class Bytecode(object):
    _immutable_ = True

    def __init__(self, code):
        self.code = code

    def __len__(self):
        return len(self.code)

    def __getitem__(self, i):
        return self.code[i]

    def __setitem__(self, i, w_x):
        self.code[i] = w_x

    def dump(self):
        lines = []
        i = 0
        while i < len(self.code):
            c = ord(self.code[i])
            name, arg_num = _bytecodes_has_args[c]
            op_str = name
            if arg_num:
                arg_str = ""
                for j in range(arg_num):
                    arg = ord(self.code[j + 1])
                    arg_str = arg_str + ", " + str(arg)
                op_str = op_str + arg_str
                i += arg_num
            lines.append(op_str + ",")
            i += 1

        return '\n'.join(lines)


def assemble(mylist):
    return ''.join([chr(x) for x in mylist])


def compile(file_name):
    # see ../tlopcode.py
    pass
