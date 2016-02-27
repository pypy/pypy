class W_Root(object):
    pass

class W_ListObject(W_Root):
    def __init__(self):
        self.items = []

def entry_point(argv):
    pass
    #bytecode = argv[0]
    #pc = 0
    #end = len(bytecode)
    #stack = Stack(512)
    #while i < end:
    #    opcode = ord(bytecode[i])
    #    if opcode == 0x0:
    #        stack.push(space.new_list())
    #    elif opcode == 0x1:
    #        w_elem = stack.pop()
    #        w_list = stack.pick(0)
    #        space.list_append(w_list, w_elem)
    #    i += 1
    #return 0
