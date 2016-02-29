from rpython.rlib.rstruct.runpack import runpack
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.jit.backend.llsupport.tl import code, stack

class W_Root(object):
    pass

class W_ListObject(W_Root):
    def __init__(self, items):
        self.items = items

    def concat(self, w_lst):
        assert isinstance(w_lst, W_ListObject)
        return self.items + w_lst.items

class W_IntObject(W_Root):
    def __init__(self, value):
        self.value = value

    def compare(self, w_int):
        assert isinstance(w_int, W_IntObject)
        return cmp(self.value, w_int.value)

class W_StrObject(W_Root):
    def __init__(self, value):
        self.value = value

    def concat(self, w_str):
        assert isinstance(w_str, W_StrObject)
        return self.value + w_str.value

class Space(object):
    @specialize.argtype(1)
    def wrap(self, val):
        if isinstance(val, W_Root):
            return val
        if isinstance(val, int):
            return W_IntObject(val)
        if isinstance(val, str):
            return W_StrObject(val)
        if isinstance(val, unicode):
            return W_StrObject(val.encode('utf-8'))
        if isinstance(val, list):
            return W_ListObject(val)
        raise NotImplementedError("cannot handle: " + str(val) + str(type(val)))

def entry_point(argv):
    bytecode = argv[0]
    pc = 0
    end = len(bytecode)
    stack = Stack(16)
    space = space.Space()
    consts = []
    while i < end:
        i = dispatch_once(space, i, bytecode, consts, stack)
    return 0

@always_inline
def dispatch_once(space, i, bytecode, consts, stack):
    opcode = ord(bytecode[i])
    if opcode == code.PutInt.BYTE_CODE:
        integral = runpack('i', bytecode[i+1:i+5])
        stack.append(space.wrap(integral))
        i += 4
    elif opcode == code.CompareInt.BYTE_CODE:
        w_int2 = stack.pop()
        w_int1 = stack.pop()
        w_int3 = space.wrap(w_int1.compare(w_int2))
        stack.append(w_int3)
    elif opcode == code.LoadStr.BYTE_CODE:
        pos = runpack('h', bytecode[i+1:i+3])
        w_str = space.wrap(consts[pos])
        stack.append(w_str)
        i += 2
    elif opcode == code.AddStr.BYTE_CODE:
        w_str2 = stack.pop()
        w_str1 = stack.pop()
        stack.append(space.wrap(w_str1.concat(w_str2)))
    elif opcode == code.AddList.BYTE_CODE:
        w_lst2 = stack.pop()
        w_lst1 = stack.pop()
        stack.append(space.wrap(w_lst1.concat(w_lst2)))
    elif opcode == code.CreateList.BYTE_CODE:
        size = runpack('h', bytecode[i+1:i+3])
        stack.append(space.wrap([None] * size))
        i += 2
    else:
        raise NotImplementedError
    return i + 1
