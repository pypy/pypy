
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from pypy.jit.metainterp.history import TreeLoop, BoxInt, BoxPtr, ConstInt
from pypy.jit.metainterp.resoperation import rop, ResOperation

class ParseError(Exception):
    pass

class OpParser(object):
    def __init__(self, descr):
        self.descr = descr
        self.vars = {}

    def box_for_var(self, elem):
        if elem.startswith('i'):
            # integer
            box = BoxInt()
        elif elem.startswith('p'):
            # pointer
            box = BoxPtr()
        else:
            raise ParseError("Unknown variable type: %s" % elem)
        return box

    def parse_header_line(self, line):
        elements = line.split(",")
        vars = []
        for elem in elements:
            elem = elem.strip()
            box = self.box_for_var(elem)
            vars.append(box)
            self.vars[elem] = box
        return vars

    def getvar(self, arg):
        try:
            return ConstInt(int(arg))
        except ValueError:
            return self.vars[arg]

    def parse_op(self, line):
        num = line.find('(')
        if num == -1:
            raise ParseError("invalid line: %s" % line)
        opname = line[:num]
        try:
            opnum = getattr(rop, opname.upper())
        except AttributeError:
            raise ParseError("unknown op: %s" % opname)
        endnum = line.find(')')
        if endnum == -1:
            raise ParseError("invalid line: %s" % line)
        argspec = line[num + 1:endnum]
        if not argspec.strip():
            return opnum, [], None
        allargs = argspec.split(",")
        args = []
        for arg in allargs:
            arg = arg.strip()
            try:
                args.append(self.getvar(arg))
            except KeyError:
                raise ParseError("Unknown var: %s" % arg)
        return opnum, args, None

    def parse_result_op(self, line):
        res, op = line.split("=")
        res = res.strip()
        op = op.strip()
        opnum, args, descr = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        rvar = self.box_for_var(res)
        self.vars[res] = rvar
        return ResOperation(opnum, args, rvar, descr)

    def parse_op_no_result(self, line):
        opnum, args, descr = self.parse_op(line)
        return ResOperation(opnum, args, None, descr)

    def parse_next_op(self, line):
        if "=" in line:
            return self.parse_result_op(line)
        else:
            return self.parse_op_no_result(line)

    def parse(self):
        lines = self.descr.split("\n")
        inpargs = None
        ops = []
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue # a comment
            if inpargs is None:
                if not line.startswith('[') or not line.endswith(']'):
                    raise ParseError("Wrong header: %s" % line)
                inpargs = self.parse_header_line(line[1:-1])
            else:
                ops.append(self.parse_next_op(line))
        loop = TreeLoop("loop")
        loop.operations = ops
        loop.inputargs = inpargs
        return loop

def parse(descr):
    return OpParser(descr).parse()
