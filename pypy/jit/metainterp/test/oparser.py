
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from pypy.jit.metainterp.history import TreeLoop, BoxInt, ConstInt,\
     ConstAddr, ConstObj, ConstPtr, Box, BasicFailDescr, BoxFloat, ConstFloat,\
     LoopToken
from pypy.jit.metainterp.resoperation import rop, ResOperation
from pypy.jit.metainterp.typesystem import llhelper
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype
from pypy.rpython.annlowlevel import llstr

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

def default_fail_descr(fail_args=None):
    return BasicFailDescr()


class OpParser(object):
    def __init__(self, input, cpu, namespace, type_system, boxkinds,
                 invent_fail_descr=default_fail_descr):
        self.input = input
        self.vars = {}
        self.cpu = cpu
        self._consts = namespace
        self.type_system = type_system
        self.boxkinds = boxkinds or {}
        if namespace is not None:
            self._cache = namespace.setdefault('_CACHE_', {})
        else:
            self._cache = {}
        self.invent_fail_descr = invent_fail_descr
        self.looptoken = LoopToken()

    def get_const(self, name, typ):
        if self._consts is None:
            return name
        obj = self._consts[name]
        if self.type_system == 'lltype':
            if typ == 'ptr':
                return ConstPtr(obj)
            else:
                assert typ == 'class'
                return ConstAddr(llmemory.cast_ptr_to_adr(obj),
                                 self.cpu)
        else:
            if typ == 'ptr':
                return ConstObj(obj)
            else:
                assert typ == 'class'
                return ConstObj(ootype.cast_to_object(obj))

    def get_descr(self, poss_descr):
        if poss_descr.startswith('<'):
            return None
        else:
            return self._consts[poss_descr]

    def box_for_var(self, elem):
        try:
            return self._cache[self.type_system, elem]
        except KeyError:
            pass
        if elem.startswith('i'):
            # integer
            box = BoxInt()
            _box_counter_more_than(elem[1:])
        elif elem.startswith('f'):
            box = BoxFloat()
            _box_counter_more_than(elem[1:])
        elif elem.startswith('p'):
            # pointer
            ts = getattr(self.cpu, 'ts', llhelper)
            box = ts.BoxRef()
            _box_counter_more_than(elem[1:])
        else:
            for prefix, boxclass in self.boxkinds.iteritems():
                if elem.startswith(prefix):
                    box = boxclass()
                    break
            else:
                raise ParseError("Unknown variable type: %s" % elem)
        self._cache[self.type_system, elem] = box
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

    def is_float(self, arg):
        try:
            float(arg)
            return True
        except ValueError:
            return False

    def getvar(self, arg):
        if not arg:
            return ConstInt(0)
        try:
            return ConstInt(int(arg))
        except ValueError:
            if self.is_float(arg):
                return ConstFloat(float(arg))
            if arg.startswith('"') or arg.startswith("'"):
                # XXX ootype
                info = arg.strip("'\"")
                return ConstPtr(lltype.cast_opaque_ptr(llmemory.GCREF,
                                                       llstr(info)))
            if arg.startswith('ConstClass('):
                name = arg[len('ConstClass('):-1]
                return self.get_const(name, 'class')
            elif arg == 'None':
                return None
            elif arg == 'NULL':
                if self.type_system == 'lltype':
                    return ConstPtr(ConstPtr.value)
                else:
                    return ConstObj(ConstObj.value)
            elif arg.startswith('ConstPtr('):
                name = arg[len('ConstPtr('):-1]
                return self.get_const(name, 'ptr')
            return self.vars[arg]

    def parse_op(self, line):
        num = line.find('(')
        if num == -1:
            raise ParseError("invalid line: %s" % line)
        opname = line[:num]
        try:
            opnum = getattr(rop, opname.upper())
        except AttributeError:
            if opname == 'escape':
                opnum = -123
            else:
                raise ParseError("unknown op: %s" % opname)
        endnum = line.rfind(')')
        if endnum == -1:
            raise ParseError("invalid line: %s" % line)
        args = []
        descr = None
        argspec = line[num + 1:endnum]
        if argspec.strip():
            if opname == 'debug_merge_point':
                allargs = [argspec]
            else:
                allargs = argspec.split(",")

            poss_descr = allargs[-1].strip()
            if poss_descr.startswith('descr='):
                descr = self.get_descr(poss_descr[len('descr='):])
                allargs = allargs[:-1]        
            for arg in allargs:
                arg = arg.strip()
                try:
                    args.append(self.getvar(arg))
                except KeyError:
                    raise ParseError("Unknown var: %s" % arg)
        if rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST:
            i = line.find('[', endnum) + 1
            j = line.find(']', i)
            if i <= 0 or j <= 0:
                raise ParseError("missing fail_args for guard operation")
            fail_args = []
            if i < j:
                for arg in line[i:j].split(','):
                    arg = arg.strip()
                    if arg == 'None':
                        fail_arg = None
                    else:
                        try:
                            fail_arg = self.vars[arg]
                        except KeyError:
                            raise ParseError(
                                "Unknown var in fail_args: %s" % arg)
                    fail_args.append(fail_arg)
            if descr is None and self.invent_fail_descr:
                descr = self.invent_fail_descr(fail_args)
            if hasattr(descr, '_oparser_uses_descr_of_guard'):
                descr._oparser_uses_descr_of_guard(self, fail_args)
        else:
            fail_args = None
            if opnum == rop.FINISH:
                if descr is None and self.invent_fail_descr:
                    descr = self.invent_fail_descr()
            elif opnum == rop.JUMP:
                if descr is None and self.invent_fail_descr:
                    descr = self.looptoken
        return opnum, args, descr, fail_args

    def parse_result_op(self, line):
        res, op = line.split("=", 1)
        res = res.strip()
        op = op.strip()
        opnum, args, descr, fail_args = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        rvar = self.box_for_var(res)
        self.vars[res] = rvar
        res = ResOperation(opnum, args, rvar, descr)
        res.fail_args = fail_args
        return res

    def parse_op_no_result(self, line):
        opnum, args, descr, fail_args = self.parse_op(line)
        res = ResOperation(opnum, args, None, descr)
        res.fail_args = fail_args
        return res

    def parse_next_op(self, line):
        if "=" in line and line.find('(') > line.find('='):
            return self.parse_result_op(line)
        else:
            return self.parse_op_no_result(line)

    def parse(self):
        lines = self.input.splitlines()
        ops = []
        newlines = []
        for line in lines:
            # for simplicity comments are not allowed on
            # debug_merge_point lines
            if '#' in line and 'debug_merge_point(' not in line:
                if line.lstrip()[0] == '#': # comment only
                    continue
                comm = line.rfind('#')
                rpar = line.find(')') # assume there's a op(...)
                if comm > rpar:
                    line = line[:comm].rstrip()
            if not line.strip():
                continue  # a comment or empty line
            newlines.append(line)
        base_indent, inpargs = self.parse_inpargs(newlines[0])
        newlines = newlines[1:]
        num, ops = self.parse_ops(base_indent, newlines, 0)
        if num < len(newlines):
            raise ParseError("unexpected dedent at line: %s" % newlines[num])
        loop = ExtendedTreeLoop("loop")
        loop.token = self.looptoken
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
                raise ParseError("indentation not valid any more")
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

def parse(input, cpu=None, namespace=None, type_system='lltype',
          boxkinds=None, invent_fail_descr=default_fail_descr,
          no_namespace=False):
    if namespace is None and not no_namespace:
        namespace = {}
    return OpParser(input, cpu, namespace, type_system, boxkinds,
                    invent_fail_descr).parse()

def pure_parse(*args, **kwds):
    kwds['invent_fail_descr'] = None
    return parse(*args, **kwds)


def _box_counter_more_than(s):
    if s.isdigit():
        Box._counter = max(Box._counter, int(s)+1)
