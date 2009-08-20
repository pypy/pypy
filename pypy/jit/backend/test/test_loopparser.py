
import py
from pypy.jit.backend.loopparser import *

class TestParser(object):
    def parse(self, name):
        parser = Parser()
        return parser.parse(py.magic.autopath().join('..', 'loopdata', name))

    def test_simple_loop(self):
        topblock, = self.parse('simple.ops')
        assert len(topblock.inputargs) == 3
        for arg in topblock.inputargs:
            assert isinstance(arg, BoxInt)
        assert len(topblock.operations) == 7
        assert isinstance(topblock.operations[0], Comment)
        assert topblock.operations[0].text == \
            "(no jitdriver.get_printable_location!)"
        assert isinstance(topblock.operations[-2], Comment)
        assert isinstance(topblock.operations[4], GuardOperation)
        assert ([op.opname for op in topblock.operations
                 if not isinstance(op, Comment)] ==
                ['int_add', 'int_sub', 'int_gt', 'guard_true', 'jump'])
        subops = topblock.operations[4].suboperations
        assert len(subops) == 1
        assert subops[0].opname == 'fail'
        fail = subops[0]
        assert len(fail.args) == 3
        assert fail.descr == []
        add = topblock.operations[1]
        assert len(add.args) == 2
        assert isinstance(add.args[0], BoxInt)
        assert add.args[0].value == 18
        assert isinstance(add.args[1], BoxInt)
        assert add.args[1].value == 6
        assert isinstance(add.result, BoxInt)
        assert isinstance(topblock.operations[2].args[1], ConstInt)
        assert topblock.operations[2].args[1].value == 1
        assert topblock.operations[2].result is topblock.operations[3].args[0]
        assert topblock.operations[3].args[1].value == -42

    def test_two_paths(self):
        loops = self.parse("two_paths.ops")
        assert len(loops) == 4
        one = loops[0]
        guard = one.operations[1]
        assert not guard.args
        call = loops[1].operations[3]
        assert call.opname == "call"
        assert len(call.args) == 4
        assert isinstance(call.args[0], ConstAddr)
        assert call.args[0].value == 166630900
        for arg in call.args[1:]:
            assert isinstance(arg, BoxInt)
        assert call.descr == [3, 0, False]
        last = loops[-1]
        nested_guard = last.operations[2].suboperations[5]
        assert isinstance(nested_guard, GuardOperation)
        assert nested_guard.opname == "guard_true"
        assert len(nested_guard.args) == 1
        assert isinstance(nested_guard.args[0], BoxInt)

    def test_string_loop(self):
        loops = self.parse("string.ops")
        assert len(loops) == 3
        newstr = loops[1].operations[1]
        assert newstr.opname == "newstr"
        assert isinstance(newstr.result, BoxPtr)
        assert len(newstr.args) == 1
        assert isinstance(newstr.args[0], ConstInt)
        assert newstr.result.value == 177102832
        assert newstr.result is loops[1].operations[2].args[0]
