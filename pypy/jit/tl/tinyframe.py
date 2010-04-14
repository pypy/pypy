
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
LOAD_FUNCTION <name> => r # load a function named name into register r
LOAD <int constant> => r # load an integer constant into register r
RETURN r1
JUMP @label # jump + or - by x opcodes
JUMP_IF_ABOVE r1 r2 @label # jump if value in r1 is above
# value in r2

function argument always comes in r0
"""

opcodes = ['ADD', 'INTROSPECT', 'PRINT', 'CALL', 'LOAD', 'LOAD_FUNCTION',
           'RETURN', 'JUMP', 'JUMP_IF_ABOVE']
for i, opcode in enumerate(opcodes):
    globals()[opcode] = i

class Code(object):
    def __init__(self, code, regno, functions):
        self.code = code
        self.regno = regno
        self.functions = functions

class Parser(object):

    name = None
    
    def compile(self, strrepr):
        self.code = []
        self.maxregno = 0
        self.functions = {}
        self.labels = {}
        lines = strrepr.splitlines()
        for line in lines:
            comment = line.find('#')
            if comment != -1:
                line = line[:comment]
            line = line.strip()
            if not line:
                continue
            if line.endswith(':'):
                # a name
                self.finish_currect_code()
                self.name = line[:-1]
                continue
            if line.startswith('@'):
                self.labels[line[1:]] = len(self.code)
                continue
            opcode, args = line.split(" ", 1)
            getattr(self, 'compile_' + opcode)(args)
        functions = [code for i, code in sorted(self.functions.values())]
        assert self.name == 'main'
        return Code("".join([chr(i) for i in self.code]), self.maxregno + 1,
                    functions)

    def finish_currect_code(self):
        if self.name is None:
            assert not self.code
            return
        code = Code("".join([chr(i) for i in self.code]), self.maxregno + 1,
                    [])
        self.functions[self.name] = (len(self.functions), code)
        self.name = None
        self.labels = {}
        self.code = []
        self.maxregno = 0

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

    def compile_JUMP_IF_ABOVE(self, args):
        arg0, arg1, label = args.split(" ")
        self.code += [JUMP_IF_ABOVE, self.rint(arg0.strip()),
                      self.rint(arg1.strip()), self.labels[label[1:]]]

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

    def gt(self, other):
        raise NotImplementedError("abstract base class")

class Int(Object):
    def __init__(self, val):
        self.val = val

    def add(self, other):
        return Int(self.val + other.val)

    def gt(self, other):
        return self.val > other.val

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
            elif opcode == JUMP_IF_ABOVE:
                arg0 = self.registers[ord(code[i + 1])]
                arg1 = self.registers[ord(code[i + 2])]
                tgt = ord(code[i + 3])
                if arg0.gt(arg1):
                    i = tgt
                else:
                    i += 4
            else:
                raise Exception("unimplemented opcode %s" % opcodes[opcode])

def interpret(code):
    return Frame(code).interpret()
