from pypy.rlib.objectmodel import hint, _is_early_constant


class Box:
    pass

class IntBox(Box):
    def __init__(self, intval):
        self.intval = intval
    def as_int(self):
        return self.intval
    def as_str(self):
        return str(self.intval)

class StrBox(Box):
    def __init__(self, strval):
        self.strval = strval
    def as_int(self):
        return myint(self.strval)
    def as_str(self):
        return self.strval


def func_add_int(ix, iy): return ix + iy
def func_sub_int(ix, iy): return ix - iy
def func_mul_int(ix, iy): return ix * iy

def func_add_str(sx, sy): return sx + ' ' + sy
def func_sub_str(sx, sy): return sx + '-' + sy
def func_mul_str(sx, sy): return sx + '*' + sy

def op2(stack, func_int, func_str):
    y = stack.pop()
    hint(y.__class__, promote=True)
    x = stack.pop()
    hint(x.__class__, promote=True)
    try:
        z = IntBox(func_int(x.as_int(), y.as_int()))
    except ValueError:
        z = StrBox(func_str(x.as_str(), y.as_str()))
    stack.append(z)


def interpret(bytecode, args):
    hint(None, global_merge_point=True)
    bytecode = hint(bytecode, deepfreeze=True)
    # ------------------------------
    oldargs = args
    argcount = hint(len(oldargs), promote=True)
    args = []
    n = 0
    while n < argcount:
        hint(n, concrete=True)
        args.append(oldargs[n])
        n += 1
    # ------------------------------
    loops = []
    stack = []
    pos = 0
    while pos < len(bytecode):
        hint(None, global_merge_point=True)
        opcode = bytecode[pos]
        hint(opcode, concrete=True)
        pos += 1
        if   opcode == 'ADD': op2(stack, func_add_int, func_add_str)
        elif opcode == 'SUB': op2(stack, func_sub_int, func_sub_str)
        elif opcode == 'MUL': op2(stack, func_mul_int, func_mul_str)
        elif opcode[0] == '#':
            n = myint(opcode, start=1)
            stack.append(args[n-1])
        elif opcode.startswith('->#'):
            n = myint(opcode, start=3)
            args[n-1] = stack.pop()
        elif opcode == '{':
            loops.append(pos)
        elif opcode == '}':
            if stack.pop().as_int() == 0:
                loops.pop()
            else:
                pos = loops[-1]
                pos = hint(pos, promote=True)
        else:
            stack.append(StrBox(opcode))
    while len(stack) > 1:
        op2(stack, func_add_int, func_add_str)
    return stack.pop()


def myint_internal(s, start=0):
    if start >= len(s):
        return -1
    res = 0
    while start < len(s):
        c = s[start]
        n = ord(c) - ord('0')
        if not (0 <= n <= 9):
            return -1
        res = res * 10 + n
        start += 1
    return res

def myint(s, start=0):
    if _is_early_constant(s):
        s = hint(s, promote=True)
        start = hint(start, promote=True)
        n = myint_internal(s, start)
        if n < 0:
            raise ValueError
    else:
        n = myint_internal(s, start)
        if n < 0:
            raise ValueError
    return n


def test_main():
    main = """#1 5 ADD""".split()
    res = interpret(main, [IntBox(20)])
    assert res.as_int() == 25
    res = interpret(main, [StrBox('foo')])
    assert res.as_str() == 'foo 5'

FACTORIAL = """The factorial of #1 is
                  1 { #1 MUL #1 1 SUB ->#1 #1 }""".split()

def test_factorial():
    res = interpret(FACTORIAL, [IntBox(5)])
    assert res.as_str() == 'The factorial of 5 is 120'
