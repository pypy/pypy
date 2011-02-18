
""" This file represents a storage mechanism that let us invent unique names
for all loops and bridges, so http requests can refer to them by name
"""

import os
from pypy.tool.jitlogparser.parser import Function, Bytecode
from pypy.tool.jitlogparser.module_finder import gather_all_code_objs

class LoopStorage(object):
    def __init__(self, extrapath=None):
        self.loops = None
        self.functions = {}
        self.codes = {}
        self.extrapath = extrapath

    def load_code(self, fname):
        try:
            return self.codes[fname]
        except KeyError:
            if os.path.isabs(fname):
                res = gather_all_code_objs(fname)
            else:
                if self.extrapath is None:
                    raise IOError("Cannot find %s" % fname)
                res = gather_all_code_objs(os.path.join(self.extrapath, fname))
            self.codes[fname] = res
            return res

    def reconnect_loops(self, loops):
        """ Re-connect loops in a way that entry bridges are filtered out
        and normal bridges are associated with guards. Returning list of
        normal loops.
        """
        res = []
        guard_dict = {}
        for loop_no, loop in enumerate(loops):
            for op in loop.operations:
                if op.name.startswith('guard_'):
                    guard_dict[int(op.descr[len('<Guard'):-1])] = (op, loop)
        for loop in loops:
            if loop.comment:
                comment = loop.comment.strip()
                if 'entry bridge' in comment:
                    pass
                elif comment.startswith('# bridge out of'):
                    no = int(comment[len('# bridge out of Guard '):].split(' ', 1)[0])
                    op, parent = guard_dict[no]
                    op.bridge = loop
                    op.percentage = ((getattr(loop, 'count', 1) * 100) /
                                     max(getattr(parent, 'count', 1), 1))
                    loop.no = no
                    continue
            res.append(loop)
        self.loops = res
        return res
