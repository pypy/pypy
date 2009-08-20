
import py
from pypy.jit.backend.loopparser import *

class TestParser(object):
    def parse(self, name):
        parser = Parser()
        return parser.parse(py.magic.autopath().join('..', 'loopdata', name))

    def test_simple_loop(self):
        topblock = self.parse('simple.ops')
        assert len(topblock.operations) == 7
        assert isinstance(topblock.operations[0], Comment)
        assert isinstance(topblock.operations[-2], Comment)
        assert isinstance(topblock.operations[4], GuardOperation)
        assert ([op.opname for op in topblock.operations
                 if not isinstance(op, Comment)] ==
                ['int_add', 'int_sub', 'int_gt', 'guard_true', 'jump'])
        subops = topblock.operations[4].suboperations.operations
        assert len(subops) == 1
        assert subops[0].opname == 'fail'
