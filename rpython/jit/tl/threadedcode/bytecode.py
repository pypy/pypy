bytecodes = []
hasarg = []

def define_op(name, has_arg=False):
    globals()[name] = len(bytecodes)
    bytecodes.append(name)
    hasarg.append(has_arg)

_bytecodes_has_args = [
    ('CONST_INT', True),
    ('CONST_FLOAT', True),
    ('DUP', False),
    ('POP', False),
    ('LT', False),
    ('EQ', False),
    ('ADD', False),
    ('SUB', False),
    ('MUL', False),
    ('DIV', False),
    ('MOD', False),
    ('EXIT', False),
    ('JUMP', True),
    ('JUMP_IF', True),
    ('CALL', True),
    ('CALL_JIT', True),
    ('CALL_NORMAL', True),
    ('RET', True),
    ('NEWSTR', True),
    ('PRINT', True)
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
        self.data.append(chr(bc))
        self.data.append(chr(arg))

    def create_bytecode(self):
        return Bytecode("".join(self.data), self.functions)

class Bytecode(object):
    _immutable_fields_ = ['code', 'functions[*]']

    def __init__(self, code, functions):
        self.code = code
        self.functions = functions

    def dump(self):
        lines = []
        i = 0
        for i in range(0, len(self.code), 2):
            c = self.code[i]
            name, has_arg = bytecodes[c]
            lines.append(name)
            if has_arg:
                arg = self.code[i + 1]
                lines.append(" " + arg)

        return '\n'.join(lines)
