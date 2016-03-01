from rpython.rlib.rstruct.runpack import runpack
from rpython.rlib.objectmodel import specialize, always_inline
from rpython.jit.backend.llsupport.tl import code
from rpython.jit.backend.llsupport.tl.stack import Stack
from rpython.rlib import rstring

class W_Root(object):
    pass

class W_ListObject(W_Root):
    def __init__(self, items):
        self.items = items

    def concat(self, space, w_lst):
        assert isinstance(w_lst, W_ListObject)
        return space.wrap(self.items + w_lst.items)

class W_IntObject(W_Root):
    def __init__(self, value):
        self.value = value

    def compare(self, space, w_int):
        assert isinstance(w_int, W_IntObject)
        return space.wrap(self.value - w_int.value)

    def concat(self, space, w_obj):
        raise NotImplementedError("cannot concat int with object")

class W_StrObject(W_Root):
    def __init__(self, value):
        self.value = value

    def concat(self, space, w_str):
        assert isinstance(w_str, W_StrObject)
        return space.wrap(self.value + w_str.value)

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
        raise NotImplementedError("cannot handle: " + str(val))

def _read_all_from_file(file):
    with open(file, 'rb') as fd:
        return fd.read()

_read_bytecode_from_file = _read_all_from_file

def _read_consts_from_file(file):
    consts = []
    bytestring = _read_all_from_file(file)
    for line in bytestring.splitlines():
        consts.append(rstring.replace(line, "\\n", "\n"))
    return consts

def entry_point(argv):
    bytecode = _read_bytecode_from_file(argv[1])
    consts = _read_consts_from_file(argv[2])
    print(bytecode)
    print(consts)
    pc = 0
    end = len(bytecode)
    stack = Stack(16)
    space = Space()
    while pc < end:
        pc = dispatch_once(space, pc, bytecode, consts, stack)
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
        stack.append(w_int1.compare(space, w_int2))
    elif opcode == code.LoadStr.BYTE_CODE:
        pos = runpack('h', bytecode[i+1:i+3])
        w_str = space.wrap(consts[pos])
        stack.append(w_str)
        i += 2
    elif opcode == code.AddStr.BYTE_CODE:
        w_str2 = stack.pop()
        w_str1 = stack.pop()
        stack.append(w_str1.concat(space, w_str2))
    elif opcode == code.AddList.BYTE_CODE:
        w_lst2 = stack.pop()
        w_lst1 = stack.pop()
        stack.append(w_lst1.concat(space, w_lst2))
    elif opcode == code.CreateList.BYTE_CODE:
        size = runpack('h', bytecode[i+1:i+3])
        stack.append(space.wrap([None] * size))
        i += 2
    elif opcode == code.AppendList.BYTE_CODE:
        w_val = stack.pop()
        w_lst = stack.peek(0)
        w_lst.items.append(w_val)
    elif opcode == code.InsertList.BYTE_CODE:
        w_val = stack.pop()
        w_idx = stack.pop()
        assert isinstance(w_idx, W_IntObject)
        w_lst = stack.peek(0)
        w_lst.items[w_idx.value] = w_val
        # index error, just crash here!
    elif opcode == code.DelList.BYTE_CODE:
        w_idx = stack.pop()
        assert isinstance(w_idx, W_IntObject)
        w_lst = stack.peek(0)
        del w_lst.items[w_idx.value]
        # index error, just crash the machine!!
    else:
        print("opcode %d is not implemented" % opcode)
        raise NotImplementedError
    return i + 1
