
from pypy.rlib.jit import JitDriver


class W_Object:
    pass


class W_IntObject(W_Object):

    def __init__(self, intvalue):
        self.intvalue = intvalue

    def is_true(self):
        return self.intvalue != 0

    def add(self, w_other):
        if isinstance(w_other, W_IntObject):
            sum = self.intvalue + w_other.intvalue
            return W_IntObject(sum)
        else:
            raise OperationError


class W_StringObject(W_Object):

    def __init__(self, strvalue):
        self.strvalue = strvalue

    def is_true(self):
        return len(self.strvalue) != 0

    def add(self, w_other):
        if isinstance(w_other, W_StringObject):
            concat = self.strvalue + w_other.strvalue
            return W_StringObject(concat)
        else:
            raise OperationError

class OperationError:
    pass

# ____________________________________________________________

CONST_INT = 1
POP       = 2
ADD       = 3
RETURN    = 4
JUMP_IF   = 5
NEWSTR    = 6

# ____________________________________________________________


class Frame(object):
    _virtualizable2_ = ['stackpos', 'stack[*]']
    
    def __init__(self, bytecode):
        self.bytecode = bytecode
        self.stack = [None] * 8
        self.stackpos = 0

    def push(self, w_x):
        self.stack[self.stackpos] = w_x
        self.stackpos += 1

    def pop(self):
        self.stackpos -= 1
        assert self.stackpos >= 0
        return self.stack[self.stackpos]

    def interp(self):
        bytecode = self.bytecode
        pc = 0

        while pc < len(bytecode):
            opcode = ord(bytecode[pc])
            pc += 1

            if opcode == CONST_INT:
                value = ord(bytecode[pc])
                pc += 1
                w_z = W_IntObject(value)
                self.push(w_z)

            elif opcode == POP:
                self.pop()

            elif opcode == ADD:
                w_y = self.pop()
                w_x = self.pop()
                w_z = w_x.add(w_y)
                self.push(w_z)

            elif opcode == JUMP_IF:
                target = ord(bytecode[pc])
                pc += 1
                w_x = self.pop()
                if w_x.is_true():
                    pc = target

            elif opcode == NEWSTR:
                char = bytecode[pc]
                pc += 1
                w_z = W_StringObject(char)
                self.push(w_z)

            elif opcode == RETURN:
                w_x = self.pop()
                assert self.stackpos == 0
                return w_x

            else:
                assert False, 'Unknown opcode: %d' % opcode


def run(bytecode, w_arg):
    frame = Frame(bytecode)
    frame.push(w_arg)
    w_result = frame.interp()
    return w_result
