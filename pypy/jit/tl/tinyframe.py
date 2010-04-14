
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
RETURN r1

function argument always comes in r0
"""

opcodes = ['ADD', 'INTROSPECT', 'PRINT', 'CALL', 'LOAD', 'RETURN']
for i, opcode in enumerate(opcodes):
    globals()[opcode] = i

class Code(object):
    def __init__(self, code, regno):
        self.code = code
        self.regno = regno

class Parser(object):
    
    def compile(self, strrepr):
        self.code = []
        self.maxregno = 0
        for line in strrepr.splitlines():
            comment = line.find('#')
            if comment != -1:
                line = line[:comment]
            line = line.strip()
            if not line:
                continue
            opcode, args = line.split(" ", 1)
            getattr(self, 'compile_' + opcode)(args)
        return Code("".join([chr(i) for i in self.code]), self.maxregno + 1)

    def rint(self, arg):
        assert arg.startswith('r')
        no = int(arg[1:])
        self.maxregno = max(self.maxregno, no)
        return no

    def compile_ADD(self, args):
        args, result = args.split("=>")
        arg0, arg1 = args.strip().split(" ")
        self.code += [ADD, self.rint(arg0), self.rint(arg1),
                      self.rint(result.strip())]

    def compile_LOAD(self, args):
        arg0, result = args.split("=>")
        arg0 = arg0.strip()
        self.code += [LOAD, int(arg0), self.rint(result.strip())]

    def compile_PRINT(self, args):
        arg = self.rint(args.strip())
        self.code += [PRINT, arg]

    def compile_RETURN(self, args):
        arg = self.rint(args.strip())
        self.code += [RETURN, arg]

def compile(strrepr):
    parser = Parser()
    return parser.compile(strrepr)

def disassemble(code):
    return [ord(i) for i in code.code]

class Object(object):
    def __init__(self):
        raise NotImplementedError("abstract base class")

    def add(self, other):
        raise NotImplementedError("abstract base class")

class Int(Object):
    def __init__(self, val):
        self.val = val

    def add(self, other):
        return Int(self.val + other.val)

class Frame(object):
    def __init__(self, code):
        self.code = code
        self.registers = [None] * code.regno 

    def interpret(self):
        i = 0
        code = self.code.code
        while True:
            opcode = ord(code[i])
            if opcode == LOAD:
                self.registers[ord(code[i + 2])] = Int(ord(code[i + 1]))
                i += 3
            elif opcode == ADD:
                arg1 = self.registers[ord(code[i + 1])]
                arg2 = self.registers[ord(code[i + 2])]
                self.registers[ord(code[i + 3])] = arg1.add(arg2)
                i += 4
            elif opcode == RETURN:
                return self.registers[ord(code[i + 1])]
            else:
                raise Exception("unimplemented opcode %s" % opcodes[opcode])

def interpret(code):
    return Frame(code).interpret()
