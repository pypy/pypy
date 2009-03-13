#!/usr/bin/env python
""" A simple parser for debug output from x86 backend. used to derive
new tests from crashes
"""

import sys, py, re

class Parser(object):
    def __init__(self):
        self.boxes = {}
        self.box_creations = []
        self.operations = []
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
        raise NotImplementedError

    def _get_unique_ptr(self, val):
        try:
            return self.unique_ptrs[val]
        except KeyError:
            self.unique_ptrs[val] = len(self.unique_ptrs)
            return len(self.unique_ptrs) - 1

    def get_ptr_val(self, val):
        return 'lltype.cast_opaque_ptr(llmemory.GCREF, ptr_%d)' % self._get_unique_ptr(val)

    def register_box(self, id, name, val):
        try:
            return self.boxes[id]
        except KeyError:
            result = name.lower() + '_' + str(id)
            self.boxes[id] = result
            if name.endswith('Ptr'):
                val = self.get_ptr_val(val)
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

    def parse(self, fname):
        def pairs(lst):
            res = []
            for i in range(0, len(lst), 2):
                res.append(lst[i] + ',' + lst[i + 1])
            return res
        
        operations = []
        data = py.path.local(fname).read()
        lines = data.split("\n")
        i = 0
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
                self.operations.append((opname, parsed_args, res))
            i += 1

    def output(self):
        for box in self.box_creations:
            print " " * 4 + box
        print " " * 4 + "ops = ["
        for name, args, res in self.operations:
            print " " * 8 + "ResOperation(rop.%s, [%s], %s)," % (name.upper(), ", ".join(args), res)
        print " " * 4 + "]"
        print " " * 4 + "ops[-1].jump_target = ops[0]"
        print " " * 4 + "cpu.compile_operations(ops)"

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
    assert len(parser.operations) == 8
    assert parser.operations[1] == ('guard_value', ['boxint_5', 'constint_7'],
                                    None)
    assert len(parser.box_creations) == 8

