
""" Simplify optimize tests by allowing to write them
in a nicer fashion
"""

from rpython.jit.tool.oparser_model import get_model

from rpython.jit.metainterp.resoperation import rop, ResOperation, \
                                            ResOpWithDescr, N_aryOp, \
                                            UnaryOp, PlainResOp

class ParseError(Exception):
    pass

class ESCAPE_OP(N_aryOp, ResOpWithDescr):

    OPNUM = -123

    def getopnum(self):
        return self.OPNUM

    def getopname(self):
        return 'escape'

    def clone(self):
        op = ESCAPE_OP(self.result)
        op.initarglist(self.getarglist()[:])
        return op

class FORCE_SPILL(UnaryOp, PlainResOp):

    OPNUM = -124

    def getopnum(self):
        return self.OPNUM

    def getopname(self):
        return 'force_spill'

    def clone(self):
        op = FORCE_SPILL(self.result)
        op.initarglist(self.getarglist()[:])
        return op

    def copy_and_change(self, opnum, args=None, result=None, descr=None):
        assert opnum == self.OPNUM
        newop = FORCE_SPILL(result or self.result)
        newop.initarglist(args or self.getarglist())
        return newop


def default_fail_descr(model, opnum, fail_args=None):
    if opnum == rop.FINISH:
        return model.BasicFinalDescr()
    return model.BasicFailDescr()


class OpParser(object):

    use_mock_model = False

    def __init__(self, input, cpu, namespace, type_system, boxkinds,
                 invent_fail_descr=default_fail_descr,
                 nonstrict=False, postproces=None):
        self.input = input
        self.vars = {}
        self._postproces = postproces
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
        self.model = get_model(self.use_mock_model)
        self.original_jitcell_token = self.model.JitCellToken()

    def get_const(self, name, typ):
        if self._consts is None:
            return name
        obj = self._consts[name]
        if typ == 'ptr':
            return self.model.ConstPtr(obj)
        else:
            assert typ == 'class'
            return self.model.ConstInt(self.model.ptr_to_int(obj))

    def get_descr(self, poss_descr, allow_invent):
        if poss_descr.startswith('<'):
            return None
        try:
            return self._consts[poss_descr]
        except KeyError:
            if allow_invent:
                int(poss_descr)
                token = self.model.JitCellToken()
                tt = self.model.TargetToken(token)
                self._consts[poss_descr] = tt
                return tt
            else:
                raise

    def box_for_var(self, elem):
        try:
            return self._cache[self.type_system, elem]
        except KeyError:
            pass
        if elem.startswith('i'):
            # integer
            box = self.model.BoxInt()
            _box_counter_more_than(self.model, elem[1:])
        elif elem.startswith('f'):
            box = self.model.BoxFloat()
            _box_counter_more_than(self.model, elem[1:])
        elif elem.startswith('p'):
            # pointer
            ts = getattr(self.cpu, 'ts', self.model.llhelper)
            box = ts.BoxRef()
            _box_counter_more_than(self.model, elem[1:])
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
            return self.model.ConstInt(0)
        try:
            return self.model.ConstInt(int(arg))
        except ValueError:
            if self.is_float(arg):
                return self.model.ConstFloat(self.model.convert_to_floatstorage(arg))
            if (arg.startswith('"') or arg.startswith("'") or
                arg.startswith('s"')):
                info = arg[1:].strip("'\"")
                return self.model.get_const_ptr_for_string(info)
            if arg.startswith('u"'):
                info = arg[1:].strip("'\"")
                return self.model.get_const_ptr_for_unicode(info)
            if arg.startswith('ConstClass('):
                name = arg[len('ConstClass('):-1]
                return self.get_const(name, 'class')
            elif arg == 'None':
                return None
            elif arg == 'NULL':
                return self.model.ConstPtr(self.model.ConstPtr.value)
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
            allargs = [arg for arg in argspec.split(",")
                       if arg != '']

            poss_descr = allargs[-1].strip()
            if poss_descr.startswith('descr='):
                descr = self.get_descr(poss_descr[len('descr='):],
                                       opname == 'label')
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
                descr = self.invent_fail_descr(self.model, opnum, fail_args)
        else:
            fail_args = None
            if opnum == rop.FINISH:
                if descr is None and self.invent_fail_descr:
                    descr = self.invent_fail_descr(self.model, opnum, fail_args)
            elif opnum == rop.JUMP:
                if descr is None and self.invent_fail_descr:
                    descr = self.original_jitcell_token

        return opnum, args, descr, fail_args

    def create_op(self, opnum, args, result, descr, fail_args):
        if opnum == ESCAPE_OP.OPNUM:
            op = ESCAPE_OP(result)
            op.initarglist(args)
            assert descr is None
            return op
        if opnum == FORCE_SPILL.OPNUM:
            op = FORCE_SPILL(result)
            op.initarglist(args)
            assert descr is None
            return op
        else:
            res = ResOperation(opnum, args, result, descr)
            if fail_args is not None:
                res.setfailargs(fail_args)
            if self._postproces:
                self._postproces(res)
            return res

    def parse_result_op(self, line):
        res, op = line.split("=", 1)
        res = res.strip()
        op = op.strip()
        opnum, args, descr, fail_args = self.parse_op(op)
        if res in self.vars:
            raise ParseError("Double assign to var %s in line: %s" % (res, line))
        rvar = self.box_for_var(res)
        self.vars[res] = rvar
        res = self.create_op(opnum, args, rvar, descr, fail_args)
        return res

    def parse_op_no_result(self, line):
        opnum, args, descr, fail_args = self.parse_op(line)
        res = self.create_op(opnum, args, None, descr, fail_args)
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
            # debug_merge_point or jit_debug lines
            if '#' in line and ('debug_merge_point(' not in line and
                                'jit_debug(' not in line):
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
        loop = self.model.ExtendedTreeLoop("loop")
        loop.comment = first_comment
        loop.original_jitcell_token = self.original_jitcell_token
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

    def postprocess(self, loop):
        """ A hook that can be overloaded to do some postprocessing
        """
        return loop

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
          no_namespace=False, nonstrict=False, OpParser=OpParser,
          postprocess=None):
    if namespace is None and not no_namespace:
        namespace = {}
    return OpParser(input, cpu, namespace, type_system, boxkinds,
                    invent_fail_descr, nonstrict, postprocess).parse()

def pure_parse(*args, **kwds):
    kwds['invent_fail_descr'] = None
    return parse(*args, **kwds)


def _box_counter_more_than(model, s):
    if s.isdigit():
        model.Box._counter = max(model.Box._counter, int(s)+1)
