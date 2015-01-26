
""" Bytecode for storage in asmmemmgr.jit_codemap. Format is as follows:

 list of tuples of shape (addr, machine code size, bytecode info)
 where bytecode info is a string made up of:
    8 bytes unique_id, 4 bytes start_addr (relative), 4 bytes size (relative),
    2 bytes how many items to skip to go to the next on similar level
    [so far represented by a list of integers for simplicity]

"""

from rpython.jit.backend.llsupport.asmmemmgr import unpack_traceback

class CodemapBuilder(object):
    def __init__(self):
        self.l = []
        self.patch_position = []
        self.last_call_depth = -1

    def debug_merge_point(self, op, pos):
        call_depth = op.getarg(1).getint()
        if call_depth != self.last_call_depth:
            unique_id = op.getarg(3).getint()
            if unique_id == 0: # uninteresting case
                return
            assert unique_id & 1 == 0
            if call_depth > self.last_call_depth:
                self.l.append(unique_id)
                self.l.append(pos) # <- this is a relative pos
                self.patch_position.append(len(self.l))
                self.l.append(0) # marker
                self.l.append(0) # second marker
            else:
                to_patch = self.patch_position.pop()
                self.l[to_patch] = pos
                self.l[to_patch + 1] = len(self.l)
            self.last_call_depth = call_depth

    def inherit_code_from_position(self, pos):
        lst = unpack_traceback(pos)
        self.last_call_depth = len(lst) - 1
        for item in lst:
            self.l.append(item)
            self.l.append(0)
            self.patch_position.append(len(self.l))
            self.l.append(0) # marker
            self.l.append(0) # second marker

    def get_final_bytecode(self, addr, size):
        while self.patch_position:
            pos = self.patch_position.pop()
            self.l[pos] = size
            self.l[pos + 1] = len(self.l)
        return (addr, size, self.l) # XXX compact self.l

