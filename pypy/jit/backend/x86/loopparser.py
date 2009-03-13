#!/usr/bin/env python
""" A parser for debug output from x86 backend. used to derive
new tests from crashes
"""

import sys, py, re

def pairs(lst):
    res = []
    for i in range(0, len(lst), 2):
        res.append(lst[i] + ',' + lst[i + 1])
    return res

class Loop(object):
    def __init__(self, operations, guard_op):
        self.operations = operations
        self.guard_op   = guard_op

class Call(object):
    def __init__(self, name, args):
        self.name = name
        self.args = args

class GuardFailure(object):
    def __init__(self, index, jmp_from, args):
        self.index = index
        self.jmp_from = jmp_from
        self.args = args

class Parser(object):
    def __init__(self):
        self.boxes = {}
        self.box_creations = []
        self.blocks = []
        self.unique_ptrs = {}

    def parse_name(self, name):
        if name == 'bp':
            return 'BoxPtr'
        elif name == 'bi':
            return 'BoxInt'
        elif name == 'ci':
            return 'ConstInt'
        elif name == 'cp':
            return 'ConstPtr'
        elif name == 'ca':
            return 'ConstAddr'
        raise NotImplementedError

    def _get_unique_ptr(self, val):
        try:
            return self.unique_ptrs[val]
        except KeyError:
            self.unique_ptrs[val] = len(self.unique_ptrs)
            return len(self.unique_ptrs) - 1

    def get_ptr_val(self, val):
        return 'lltype.cast_opaque_ptr(llmemory.GCREF, ptr_%d)' % self._get_unique_ptr(val)

    def get_adr_val(self, val):
        return 'llmemory.cast_ptr_to_adr(ptr_%d)' % self._get_unique_ptr(val)

    def register_box(self, id, name, val):
        try:
            return self.boxes[id]
        except KeyError:
            result = name.lower() + '_' + str(id)
            self.boxes[id] = result
            if name.endswith('Ptr'):
                val = self.get_ptr_val(val)
            elif name == 'ConstAddr':
                val = self.get_adr_val(val)
            self.box_creations.append('%s = %s(%s)' % (result, name, val))
            return result

    def parse_args(self, args):
        res = []
        for arg in args:
            m = re.match('(\w\w)\((\d+),(\d+)\)', arg)
            name = self.parse_name(m.group(1))
            id   = int(m.group(2))
            val  = int(m.group(3))
            unique_box = self.register_box(id, name, val)
            res.append(unique_box)
        return res

    def parse_loop(self, lines):        
        i = 0
        operations = []
        if lines[0].startswith('GO'):
            guard_op = int(re.search('\((-?\d+)\)', lines[0]).group(1))
            i = 1
        else:
            guard_op = None
        while i < len(lines):
            line = lines[i]
            if line:
                opname, args = line.split(' ')
                if args:
                    parsed_args = self.parse_args(pairs(args.split(",")))
                else:
                    parsed_args = []
                if i + 1 < len(lines) and lines[i + 1].startswith('  =>'):
                    i += 1
                    box = lines[i][5:]
                    [res] = self.parse_args([box])
                else:
                    res = None
                if i + 1 < len(lines) and lines[i + 1].startswith('  ..'):
                    i += 1
                    liveboxes = lines[i][5:]
                    liveboxes = self.parse_args(pairs(liveboxes.split(",")))
                else:
                    liveboxes = None
                operations.append((opname, parsed_args, res, liveboxes))
            i += 1
        return Loop(operations, guard_op)

    def parse_call(self, line):
        name, args = line.split(" ")
        return Call(name, self.parse_args(pairs(args.split(","))))

    def parse_guard_failure(self, line):
        index, jmp_from, args = line.split(" ")
        return GuardFailure(index, jmp_from, self.parse_args(pairs(args.split(","))))

    def parse(self, fname):
        data = py.path.local(fname).read()
        lines = data.split("\n")
        i = 0
        while i < len(lines):
            if lines[i] == '<<<<<<<<<<':
                # a loop
                j = i
                while lines[j] != '>>>>>>>>>>':
                    j += 1
                self.blocks.append(self.parse_loop(lines[i+1:j]))
                i = j + 1
            elif lines[i] == 'CALL':
                self.blocks.append(self.parse_call(lines[i+1]))
                i += 2
            elif lines[i] == 'xxxxxxxxxx':
                assert lines[i + 2] == 'xxxxxxxxxx'
                self.blocks.append(self.parse_guard_failure(lines[i + 1]))
                i += 3
            elif not lines[i]:
                i += 1
            else:
                xxxx

    def output(self):
        for val, num in self.unique_ptrs.items():
            print " " * 4 + "ptr_%d = xxx(%d)" % (num, val)
        for box in self.box_creations:
            print " " * 4 + box
        for block in self.blocks:
            if isinstance(block, Loop):
                if block.operations[-1][0] == '<119>':
                    continue
                print " " * 4 + "ops = ["
                d = {}
                for i, (name, args, res, liveboxes) in enumerate(block.operations):
                    print " " * 8 + "ResOperation(rop.%s, [%s], %s)," % (name.upper(), ", ".join(args), res)
                    if liveboxes is not None:
                        d[i] = liveboxes
                for k, v in d.items():
                    print " " * 4 + "ops[%d].liveboxes = [%s]" % (k, ", ".join(v))
                print " " * 4 + "]"
                print " " * 4 + "ops[-1].jump_target = ops[0]"
                print " " * 4 + "cpu.compile_operations(ops)"
            if isinstance(block, Call):
                if block.name == 'call':
                    continue # ignore calls to single function
                print " " * 4 + "cpu.execute_operations_in_new_frame('%s', [%s])" % (block.name, ", ".join(block.args))
            if isinstance(block, GuardFailure):
                expected = "[" + ", ".join(["%s.value" % arg for arg in block.args]) + "]"
                print " " * 4 + "expected = " + expected
                print " " * 4 + "assert meta_interp.recordedvalues = expected"

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print __doc__
        sys.exit(1)
    parser = Parser()
    parser.parse(sys.argv[1])
    parser.output()

def test_loopparser():
    parser = Parser()
    parser.parse(py.magic.autopath().join('..', 'inp'))
    assert len(parser.blocks[0].operations) == 10
    assert parser.blocks[0].operations[1] == ('int_add',
      ['boxint_2', 'boxint_0'], 'boxint_3', None)
    assert len(parser.box_creations) == 13

