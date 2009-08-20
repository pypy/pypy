#!/usr/bin/env python
""" A parser for debug output from x86 backend. used to derive
new tests from crashes
"""

import sys, py, re

def count_indent(s):
    indent = 0
    for char in s:
        if char != " ":
            break
        indent += 1
    return indent

class EndOfBlock(Exception):
    pass

class Block(object):
    def __init__(self):
        self.operations = []

    def add(self, element):
        self.operations.append(element)

class Comment(object):
    def __init__(self, text):
        self.text = text

class Operation(object):
    def __init__(self, opname, args, result=None, descr=None):
        self.opname = opname
        self.args   = args
        self.result = result
        self.descr = descr

    def __repr__(self):
        if self.result is None:
            return "%s(%s)" % (self.opname, self.args)
        return "%s = %s(%s)" % (self.result, self.opname, self.args)

class GuardOperation(Operation):

    @property
    def suboperations(self):
        return self.subblock.operations

class AbstractValue(object):

    def __init__(self, value):
        self.value = int(value)

class Box(AbstractValue):
    pass

class BoxInt(Box):
    pass

class BoxAddr(Box):
    pass

class BoxPtr(Box):
    pass

class Const(AbstractValue):
    pass

class ConstInt(Const):
    pass

class ConstAddr(Const):
    pass

class ConstPtr(Const):
    pass

box_map = {
    'b' : {
        'i' : BoxInt,
        'a' : BoxAddr,
        'p' : BoxPtr
        },
    'c' : {
        'i' : ConstInt,
        'a' : ConstAddr,
        'p' : ConstPtr
        },
}


_arg_finder = re.compile(r"(..)\((\d+),(\d+)\)")

class Parser(object):

    current_indentation = 0

    def parse(self, fname):
        self.current_block = Block()
        self.blockstack = []
        self.boxes = {}
        data = py.path.local(fname).read()
        lines = data.splitlines()
        i = 0
        length = len(lines)
        loops = []
        while i < length:
             i = self._parse(lines, i)
             loops.append(self.current_block)
             self.boxes = {}
             self.current_block = Block()
        assert not self.blockstack
        return loops

    def _parse_boxes(self, box_string):
        boxes = []
        for info, iden, value in _arg_finder.findall(box_string):
            box = self.get_box(iden, info, value)
            boxes.append(self.get_box(int(iden), info, value))
        return boxes

    def get_box(self, key, tp_info, value):
        try:
            node = self.boxes[key]
        except KeyError:
            box_type, tp = tp_info
            klass = box_map[box_type][tp]
            node = klass(value)
            self.boxes[key] = node
        assert node.__class__ is box_map[tp_info[0]][tp_info[1]]
        return node

    def parse_result(self, result):
        return result

    def parse_inputargs(self, inputargs):
        return inputargs

    def parse_block(self, lines, start, guard_op):
        self.blockstack.append(self.current_block)
        block = Block()
        guard_op.subblock = block
        self.current_block = block
        res = self._parse(lines, start)
        self.current_block = self.blockstack.pop()
        self.current_indentation -= 2
        return res

    def parse_next_instruction(self, lines, i):
        line = lines[i].strip()
        if line.startswith('LOOP END'):
            raise EndOfBlock()
        if line.startswith('LOOP'):
            _, inputargs = line.split(" ")
            self.current_block.inputargs = self.parse_inputargs(inputargs)
            return i + 1
        if line.startswith('END'):
            raise EndOfBlock()
        if line.startswith('#'):
            self.current_block.add(Comment(line[1:]))
            return i + 1
        descr = None
        if " " in line:
            # has arguments
            opname, args_string = line.split(" ")
            args = self._parse_boxes(args_string)
            bracket = args_string.find("[")
            if bracket != -1:
                assert args_string[-1] == "]"
                descr = eval(args_string[bracket:])
        else:
            opname = line
            args = []
        _, opname = opname.split(":")
        if lines[i + 1].startswith(" " * (self.current_indentation + 2)):
            if lines[i + 1].strip().startswith('BEGIN'):
                self.current_indentation += 2
                guard_op = GuardOperation(opname, args)
                self.current_block.add(guard_op)
                return self.parse_block(lines, i + 2, guard_op)
            marker, result = lines[i + 1].strip().split(" ")
            assert marker == '=>'
            result, = self._parse_boxes(result)
            self.current_block.add(Operation(opname, args, result, descr))
            return i + 2
        else:
            self.current_block.add(Operation(opname, args, descr=descr))
            return i + 1

    def _parse(self, lines, i):
        while True:
            try:
                indentation = count_indent(lines[i])
                if indentation == self.current_indentation:
                    i = self.parse_next_instruction(lines, i)
                else:
                    xxx
            except EndOfBlock:
                return i + 1

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

class OldParser(object):
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

