
""" Interpreter for a tiny interpreter with frame introspection. Supports
integer values and function values. The machine is
register based with untyped registers.

Opcodes:
ADD r1 r2 => r3 # integer addition or function combination,
                 # depending on argument types
                 # if r1 has a function f and r2 has a function g
                 # the result will be a function lambda arg : f(g(arg))
INTROSPECT r1 => r2 # frame introspection - load a register with number
                    # pointed by r1 (must be int) to r2
PRINT r # print a register
CALL r1 r2 # call a function in register one with argument in r2
LOAD <name> => r # load a function named name into register r
LOAD <int constant> => r # load an integer constant into register r

function argument always comes in r0
"""

opcodes = ['ADD', 'INTROSPECT', 'PRINT', 'CALL', 'LOAD']
for i, opcode in enumerate(opcodes):
    globals()[opcode] = i

class Code(object):
    _immutable_ = True

    def __init__(self, code):
        code = code

def rint(arg):
    assert arg.startswith('r')
    return int(arg[1:])

class Parser(object):
    def compile(self, strrepr):
        self.code = []
        for line in strrepr.splitlines():
            comment = line.find('#')
            if comment != -1:
                line = line[:comment]
            line = line.strip()
            if not line:
                continue
            opcode, args = line.split(" ", 1)
            getattr(self, 'compile_' + opcode)(args)
        return "".join([chr(i) for i in self.code])

    def compile_ADD(self, args):
        args, result = args.split("=>")
        arg0, arg1 = args.strip().split(" ")
        self.code += [ADD, rint(arg0), rint(arg1), rint(result.strip())]

    def compile_LOAD(self, args):
        arg0, result = args.split("=>")
        arg0 = arg0.strip()
        self.code += [LOAD, int(arg0), rint(result.strip())]

    def compile_PRINT(self, args):
        arg = rint(args.strip())
        self.code += [PRINT, arg]

def compile(strrepr):
    parser = Parser()
    return parser.compile(strrepr)

def disassemble(code):
    return [ord(i) for i in code]
