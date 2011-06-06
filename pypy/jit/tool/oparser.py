
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from pypy.jit.metainterp.history import TreeLoop, BoxInt, ConstInt,\
     ConstObj, ConstPtr, Box, BasicFailDescr, BoxFloat, ConstFloat,\
     LoopToken, get_const_ptr_for_string, get_const_ptr_for_unicode
from pypy.jit.metainterp.resoperation import rop, ResOperation, \
                                            ResOpWithDescr, N_aryOp, \
                                            UnaryOp, PlainResOp
from pypy.jit.metainterp.typesystem import llhelper
from pypy.jit.codewriter.heaptracker import adr2int
from pypy.jit.codewriter import longlong
from pypy.rpython.lltypesystem import lltype, llmemory
from pypy.rpython.ootypesystem import ootype

class ParseError(Exception):
    pass

class Boxes(object):
    pass

class ESCAPE_OP(N_aryOp, ResOpWithDescr):

    OPNUM = -123

    def __init__(self, opnum, args, result, descr=None):
        assert opnum == self.OPNUM
        self.result = result
        self.initarglist(args)
        self.setdescr(descr)

    def getopnum(self):
        return self.OPNUM

    def clone(self):
        return ESCAPE_OP(self.OPNUM, self.getarglist()[:], self.result, self.getdescr())

class FORCE_SPILL(UnaryOp, PlainResOp):

    OPNUM = -124

    def __init__(self, opnum, args, result=None, descr=None):
        assert result is None
        assert descr is None
        assert opnum == self.OPNUM
        self.result = result
        self.initarglist(args)

    def getopnum(self):
        return self.OPNUM

    def clone(self):
        return FORCE_SPILL(self.OPNUM, self.getarglist()[:])

class ExtendedTreeLoop(TreeLoop):

    def getboxes(self):
        def opboxes(operations):
            for op in operations:
                yield op.result
                for box in op.getarglist():
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
                 invent_fail_descr=default_fail_descr,
                 nonstrict=False):
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
        self.nonstrict = nonstrict
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
                return ConstInt(adr2int(llmemory.cast_ptr_to_adr(obj)))
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
            vars.append(self.newvar(elem))
        return vars

    def newvar(self, elem):
        box = self.box_for_var(elem)
        self.vars[elem] = box
        return box

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
                return ConstFloat(longlong.getfloatstorage(float(arg)))
            if (arg.startswith('"') or arg.startswith("'") or
                arg.startswith('s"')):
                # XXX ootype
                info = arg[1:].strip("'\"")
                return get_const_ptr_for_string(info)
            if arg.startswith('u"'):
                # XXX ootype
                info = arg[1:].strip("'\"")
                return get_const_ptr_for_unicode(info)
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
            if arg not in self.vars and self.nonstrict:
                self.newvar(arg)
            return self.vars[arg]

    def parse_args(self, opname, argspec):
        args = []
        descr = None
        if argspec.strip():
            if opname == 'debug_merge_point':
                allargs = argspec.split(', ', 1)
            else:
                allargs = [arg for arg in argspec.split(",")
                           if arg != '']

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
        return args, descr

    def parse_op(self, line):
        num = line.find('(')
        if num == -1:
            raise ParseError("invalid line: %s" % line)
        opname = line[:num]
        try:
            opnum = getattr(rop, opname.upper())
        except AttributeError:
            if opname == 'escape':
                opnum = ESCAPE_OP.OPNUM
            elif opname == 'force_spill':
                opnum = FORCE_SPILL.OPNUM
            else:
                raise ParseError("unknown op: %s" % opname)
        endnum = line.rfind(')')
        if endnum == -1:
            raise ParseError("invalid line: %s" % line)
        args, descr = self.parse_args(opname, line[num + 1:endnum])
        if rop._GUARD_FIRST <= opnum <= rop._GUARD_LAST:
            i = line.find('[', endnum) + 1
            j = line.find(']', i)
            if (i <= 0 or j <= 0) and not self.nonstrict:
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

    def create_op(self, opnum, args, result, descr):
        if opnum == ESCAPE_OP.OPNUM:
            return ESCAPE_OP(opnum, args, result, descr)
        if opnum == FORCE_SPILL.OPNUM:
            return FORCE_SPILL(opnum, args, result, descr)
        else:
            return ResOperation(opnum, args, result, descr)

    def parse_result_op(self, line):
        res, op = line.split("=", 1)
        res = res.strip()
        op = op.strip()
        opnum, args, descr, fail_args = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        rvar = self.box_for_var(res)
        self.vars[res] = rvar
        res = self.create_op(opnum, args, rvar, descr)
        if fail_args is not None:
            res.setfailargs(fail_args)
        return res

    def parse_op_no_result(self, line):
        opnum, args, descr, fail_args = self.parse_op(line)
        res = self.create_op(opnum, args, None, descr)
        if fail_args is not None:
            res.setfailargs(fail_args)
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
        first_comment = None
        for line in lines:
            # for simplicity comments are not allowed on
            # debug_merge_point lines
            if '#' in line and 'debug_merge_point(' not in line:
                if line.lstrip()[0] == '#': # comment only
                    if first_comment is None:
                        first_comment = line
                    continue
                comm = line.rfind('#')
                rpar = line.find(')') # assume there's a op(...)
                if comm > rpar:
                    line = line[:comm].rstrip()
            if not line.strip():
                continue  # a comment or empty line
            newlines.append(line)
        base_indent, inpargs, newlines = self.parse_inpargs(newlines)
        num, ops, last_offset = self.parse_ops(base_indent, newlines, 0)
        if num < len(newlines):
            raise ParseError("unexpected dedent at line: %s" % newlines[num])
        loop = ExtendedTreeLoop("loop")
        loop.comment = first_comment
        loop.token = self.looptoken
        loop.operations = ops
        loop.inputargs = inpargs
        loop.last_offset = last_offset
        return loop

    def parse_ops(self, indent, lines, start):
        num = start
        ops = []
        last_offset = None
        while num < len(lines):
            line = lines[num]
            if not line.startswith(" " * indent):
                # dedent
                return num, ops
            elif line.startswith(" "*(indent + 1)):
                raise ParseError("indentation not valid any more")
            else:
                line = line.strip()
                offset, line = self.parse_offset(line)
                if line == '--end of the loop--':
                    last_offset = offset
                else:
                    op = self.parse_next_op(line)
                    if offset:
                        op.offset = offset
                    ops.append(op)
                num += 1
        return num, ops, last_offset

    def parse_offset(self, line):
        if line.startswith('+'):
            # it begins with an offset, like: "+10: i1 = int_add(...)"
            offset, _, line = line.partition(':')
            offset = int(offset)
            return offset, line.strip()
        return None, line

    def parse_inpargs(self, lines):
        line = lines[0]
        base_indent = len(line) - len(line.lstrip(' '))
        line = line.strip()
        if not line.startswith('[') and self.nonstrict:
            return base_indent, [], lines
        lines = lines[1:]
        if line == '[]':
            return base_indent, [], lines
        if not line.startswith('[') or not line.endswith(']'):
            raise ParseError("Wrong header: %s" % line)
        inpargs = self.parse_header_line(line[1:-1])
        return base_indent, inpargs, lines

def parse(input, cpu=None, namespace=None, type_system='lltype',
          boxkinds=None, invent_fail_descr=default_fail_descr,
          no_namespace=False, nonstrict=False):
    if namespace is None and not no_namespace:
        namespace = {}
    return OpParser(input, cpu, namespace, type_system, boxkinds,
                    invent_fail_descr, nonstrict).parse()

def pure_parse(*args, **kwds):
    kwds['invent_fail_descr'] = None
    return parse(*args, **kwds)


def _box_counter_more_than(s):
    if s.isdigit():
        Box._counter = max(Box._counter, int(s)+1)
