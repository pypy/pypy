#!/usr/bin/env python
""" A parser for debug output from x86 backend. used to derive
new tests from crashes
"""

import autopath
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

class OpContainer(object):
    def __init__(self):
        self.operations = []

    def add(self, element):
        self.operations.append(element)

    def get_operations(self):
        return self.operations

    def get_display_text(self):
        return repr(self)


class Loop(OpContainer):

    def __repr__(self):
        return "Loop"

class Block(OpContainer):

    def __repr__(self):
        return "Block"

class BaseOperation(object):

    def is_guard(self):
        return False

class Comment(BaseOperation):
    def __init__(self, text):
        self.text = text
        self.args = []
        self.result = None

    def __repr__(self):
        return "Comment: %r" % (self.text,)

class Operation(BaseOperation):
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

    def is_guard(self):
        return True

class AbstractValue(object):

    def __init__(self, iden, value):
        self.value = int(value)
        self.iden = iden

    def __repr__(self):
        klass = self.__class__.__name__
        return "%s(%s, %s)" % (klass, self.iden, self.value)

    @property
    def pretty(self):
        return "i%s" % (self.iden,)

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


_arg_finder = re.compile(r"(..)\((\d+),(-?\d+)\)")

class Parser(object):

    current_indentation = 0

    def parse(self, fname):
        self.current_block = Loop()
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
             self.current_block = Loop()
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
            node = klass(key, value)
            self.boxes[key] = node
        assert node.__class__ is box_map[tp_info[0]][tp_info[1]]
        return node

    def parse_result(self, result):
        return result

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
            self.current_block.inputargs = self._parse_boxes(inputargs)
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
        try:
            while True:
                i = self.parse_next_instruction(lines, i)
        except EndOfBlock:
            assert i < len(lines)
            return i + 1
        else:
            raise AssertionError("shouldn't happen (python bug????)")


def _write_operations(ops, level):
    def write(stuff):
        print " " * level + stuff
    for op in (op for op in ops if not isinstance(op, Comment)):
        args = [arg.pretty for arg in op.args]
        if op.descr:
            args.append("descr=%r" % (op.descr,))
        args_string = ", ".join(args)
        op_string = "%s(%s)" % (op.opname, args_string)
        if op.is_guard():
            write(op_string)
            _write_operations(op.suboperations, level + 4)
        else:
            if op.result is None:
                write(op_string)
            else:
                write("%s = %s" % (op.result.pretty, op_string))


def convert_to_oparse(loops):
    if len(loops) > 1:
        print >> sys.stderr, "there's more than one loop in that file!"
        sys.exit(1)
    loop, = loops
    print "[%s]" % (", ".join(arg.pretty for arg in loop.inputargs),)
    _write_operations(loop.operations, 0)
    sys.exit(0)


if __name__ == "__main__":
    from pypy.jit.metainterp.graphpage import display_loops
    fn = sys.argv[1]
    parser = Parser()
    loops = parser.parse(fn)
    convert_to_oparse(loops)

