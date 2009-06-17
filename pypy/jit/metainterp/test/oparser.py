
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from pypy.jit.metainterp.history import TreeLoop, BoxInt, BoxPtr, ConstInt,\
     ConstAddr, ConstObj, ConstPtr, Box
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

_cache = {}

class ParseError(Exception):
    pass


class Boxes(object):
    pass

class ExtendedTreeLoop(TreeLoop):

    def getboxes(self):
        def opboxes(operations):
            for op in operations:
                yield op.result
                for box in op.args:
                    yield box
                if op.suboperations:
                    for box in opboxes(op.suboperations):
                        yield box
        def allboxes():
            for box in self.inputargs:
                yield box
            for box in opboxes(self.operations):
                yield box

        boxes = Boxes()
        for box in allboxes():
            if isinstance(box, Box):
                name = str(box)
                setattr(boxes, name, box)
        return boxes

    def setvalues(self, **kwds):
        boxes = self.getboxes()
        for name, value in kwds.iteritems():
            getattr(boxes, name).value = value

class OpParser(object):
    def __init__(self, descr, cpu, namespace, type_system, boxkinds):
        self.descr = descr
        self.vars = {}
        self.cpu = cpu
        self.consts = namespace
        self.type_system = type_system
        self.boxkinds = boxkinds or {}

    def box_for_var(self, elem):
        try:
            return _cache[elem]
        except KeyError:
            pass
        if elem.startswith('i'):
            # integer
            box = BoxInt()
        elif elem.startswith('p'):
            # pointer
            box = BoxPtr()
        else:
            for prefix, boxclass in self.boxkinds.iteritems():
                if elem.startswith(prefix):
                    box = boxclass()
                    break
            else:
                raise ParseError("Unknown variable type: %s" % elem)
        _cache[elem] = box
        box._str = elem
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
            if arg.startswith('ConstClass('):
                name = arg[len('ConstClass('):-1]
                if self.type_system == 'lltype':
                    return ConstAddr(llmemory.cast_ptr_to_adr(self.consts[name]),
                                     self.cpu)
                else:
                    return ConstObj(ootype.cast_to_object(self.consts[name]))
            elif arg == 'None':
                return None
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
        endnum = line.rfind(')')
        if endnum == -1:
            raise ParseError("invalid line: %s" % line)
        argspec = line[num + 1:endnum]
        if not argspec.strip():
            return opnum, [], None
        allargs = argspec.split(",")
        args = []
        descr = None
        poss_descr = allargs[-1].strip()
        if poss_descr.startswith('descr='):
            descr = self.consts[poss_descr[len('descr='):]]
            allargs = allargs[:-1]        
        for arg in allargs:
            arg = arg.strip()
            try:
                args.append(self.getvar(arg))
            except KeyError:
                raise ParseError("Unknown var: %s" % arg)
        return opnum, args, descr

    def parse_result_op(self, line):
        res, op = line.split("=", 1)
        res = res.strip()
        op = op.strip()
        opnum, args, descr = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        rvar = self.box_for_var(res)
        self.vars[res] = rvar
        res = ResOperation(opnum, args, rvar, descr)
        return res

    def parse_op_no_result(self, line):
        opnum, args, descr = self.parse_op(line)
        res = ResOperation(opnum, args, None, descr)
        return res

    def parse_next_op(self, line):
        if "=" in line and line.find('(') > line.find('='):
            return self.parse_result_op(line)
        else:
            return self.parse_op_no_result(line)

    def parse(self):
        lines = self.descr.splitlines()
        ops = []
        newlines = []
        for line in lines:
            if not line.strip() or line.strip().startswith("#"):
                continue # a comment
            newlines.append(line)
        base_indent, inpargs = self.parse_inpargs(newlines[0])
        newlines = newlines[1:]
        num, ops = self.parse_ops(base_indent, newlines, 0)
        if num < len(newlines):
            raise ParseError("unexpected dedent at line: %s" % newlines[num])
        loop = ExtendedTreeLoop("loop")
        loop.operations = ops
        loop.inputargs = inpargs
        return loop

    def parse_ops(self, indent, lines, start):
        num = start
        ops = []
        while num < len(lines):
            line = lines[num]
            if not line.startswith(" " * indent):
                # dedent
                return num, ops
            elif line.startswith(" "*(indent + 1)):
                # suboperations
                new_indent = len(line) - len(line.lstrip())
                num, suboperations = self.parse_ops(new_indent, lines, num)
                ops[-1].suboperations = suboperations
            else:
                ops.append(self.parse_next_op(lines[num].strip()))
                num += 1
        return num, ops

    def parse_inpargs(self, line):
        base_indent = line.find('[')
        line = line.strip()
        if line == '[]':
            return base_indent, []
        if base_indent == -1 or not line.endswith(']'):
            raise ParseError("Wrong header: %s" % line)
        inpargs = self.parse_header_line(line[1:-1])
        return base_indent, inpargs

def parse(descr, cpu=None, namespace={}, type_system='lltype',
          boxkinds=None):
    return OpParser(descr, cpu, namespace, type_system, boxkinds).parse()
