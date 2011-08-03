import re, sys

from pypy.jit.metainterp.resoperation import opname
from pypy.jit.tool.oparser import OpParser
from pypy.tool.logparser import parse_log_file, extract_category

class Op(object):
    bridge = None
    offset = None
    asm = None

    def __init__(self, name, args, res, descr):
        self.name = name
        self.args = args
        self.res = res
        self.descr = descr
        self._is_guard = name.startswith('guard_')
        if self._is_guard:
            self.guard_no = int(self.descr[len('<Guard'):-1])

    def setfailargs(self, _):
        pass

    def getarg(self, i):
        return self._getvar(self.args[i])

    def getargs(self):
        return [self._getvar(v) for v in self.args]

    def getres(self):
        return self._getvar(self.res)

    def getdescr(self):
        return self.descr

    def _getvar(self, v):
        return v

    def is_guard(self):
        return self._is_guard

    def repr(self):
        args = self.getargs()
        if self.descr is not None:
            args.append('descr=%s' % self.getdescr())
        arglist = ', '.join(args)
        if self.res is not None:
            return '%s = %s(%s)' % (self.getres(), self.name, arglist)
        else:
            return '%s(%s)' % (self.name, arglist)

    def __repr__(self):
        return self.repr()
        ## return '<%s (%s)>' % (self.name, ', '.join([repr(a)
        ##                                             for a in self.args]))

class SimpleParser(OpParser):

    # factory method
    Op = Op
    use_mock_model = True

    def postprocess(self, loop, backend_dump=None, backend_tp=None,
                    dump_start=0):
        if backend_dump is not None:
            raw_asm = self._asm_disassemble(backend_dump.decode('hex'),
                                            backend_tp, dump_start)
            asm = []
            start = 0
            for elem in raw_asm:
                if len(elem.split("\t")) != 3:
                    continue
                adr, _, v = elem.split("\t")
                if not start:
                    start = int(adr.strip(":"), 16)
                ofs = int(adr.strip(":"), 16) - start
                if ofs >= 0:
                    asm.append((ofs, v.strip("\n")))
            asm_index = 0
            for i, op in enumerate(loop.operations):
                end = 0
                j = i + 1
                while end == 0:
                    if j == len(loop.operations):
                        end = loop.last_offset
                        break
                    if loop.operations[j].offset is None:
                        j += 1
                    else:
                        end = loop.operations[j].offset
                if op.offset is not None:
                    while asm[asm_index][0] < op.offset:
                        asm_index += 1
                    end_index = asm_index
                    while asm[end_index][0] < end and end_index < len(asm) - 1:
                        end_index += 1
                    op.asm = '\n'.join([asm[i][1] for i in range(asm_index, end_index)])
        return loop
                    
    def _asm_disassemble(self, d, origin_addr, tp):
        from pypy.jit.backend.x86.tool.viewcode import machine_code_dump
        return list(machine_code_dump(d, tp, origin_addr))

    @classmethod
    def parse_from_input(cls, input, **kwds):
        parser = cls(input, None, {}, 'lltype', None,
                     nonstrict=True)
        loop = parser.parse()
        return parser.postprocess(loop, **kwds)

    def parse_args(self, opname, argspec):
        if not argspec.strip():
            return [], None
        if opname == 'debug_merge_point':
            return argspec.split(", ", 1), None
        else:
            args = argspec.split(', ')
            descr = None
            if args[-1].startswith('descr='):
                descr = args[-1][len('descr='):]
                args = args[:-1]
            if args == ['']:
                args = []
            return (args, descr)

    def box_for_var(self, res):
        return res

    def create_op(self, opnum, args, res, descr):
        return self.Op(intern(opname[opnum].lower()), args, res, descr)



class NonCodeError(Exception):
    pass

class TraceForOpcode(object):
    filename = None
    startlineno = 0
    name = None
    code = None
    bytecode_no = 0
    bytecode_name = None
    is_bytecode = True
    inline_level = None

    def __init__(self, operations, storage):
        if operations[0].name == 'debug_merge_point':
            self.inline_level = int(operations[0].args[0])
            m = re.search('<code object ([<>\w]+)\. file \'(.+?)\'\. line (\d+)> #(\d+) (\w+)',
                         operations[0].args[1])
            if m is None:
                # a non-code loop, like StrLiteralSearch or something
                self.bytecode_name = operations[0].args[1][1:-1]
            else:
                self.name, self.filename, lineno, bytecode_no, self.bytecode_name = m.groups()
                self.startlineno = int(lineno)
                self.bytecode_no = int(bytecode_no)
        self.operations = operations
        self.storage = storage
        self.code = storage.disassemble_code(self.filename, self.startlineno,
                                             self.name)

    def repr(self):
        if self.filename is None:
            return "Unknown"
        return "%s, file '%s', line %d" % (self.name, self.filename,
                                           self.startlineno)

    def getcode(self):
        return self.code

    def has_valid_code(self):
        return self.code is not None

    def getopcode(self):
        return self.code.map[self.bytecode_no]

    def getlineno(self):
        return self.getopcode().lineno
    lineno = property(getlineno)

    def getline_starts_here(self):
        return self.getopcode().line_starts_here
    line_starts_here = property(getline_starts_here)

    def __repr__(self):
        return "[%s]" % ", ".join([repr(op) for op in self.operations])

    def pretty_print(self, out):
        pass

class Function(object):
    filename = None
    name = None
    startlineno = 0
    _linerange = None
    _lineset = None
    is_bytecode = False
    inline_level = None

    # factory method
    TraceForOpcode = TraceForOpcode

    def __init__(self, chunks, path, storage, inputargs=''):
        self.path = path
        self.inputargs = inputargs
        self.chunks = chunks
        for chunk in self.chunks:
            if chunk.filename is not None:
                self.startlineno = chunk.startlineno
                self.filename = chunk.filename
                self.name = chunk.name
                self.inline_level = chunk.inline_level
                break
        self.storage = storage

    @classmethod
    def from_operations(cls, operations, storage, limit=None, inputargs=''):
        """ Slice given operation list into a chain of TraceForOpcode chunks.
        Also detect inlined functions and make them Function
        """
        stack = []

        def getpath(stack):
            return ",".join([str(len(v)) for v in stack])

        def append_to_res(bc):
            if not stack:
                stack.append([])
            else:
                if bc.inline_level is not None and bc.inline_level + 1 != len(stack):
                    if bc.inline_level < len(stack):
                        last = stack.pop()
                        stack[-1].append(cls(last, getpath(stack), storage))
                    else:
                        stack.append([])
            stack[-1].append(bc)

        so_far = []
        stack = []
        for op in operations:
            if op.name == 'debug_merge_point':
                if so_far:
                    append_to_res(cls.TraceForOpcode(so_far, storage))
                    if limit:
                        break
                    so_far = []
            so_far.append(op)
        if so_far:
            append_to_res(cls.TraceForOpcode(so_far, storage))
        # wrap stack back up
        if not stack:
            # no ops whatsoever
            return cls([], getpath(stack), storage, inputargs)
        while True:
            next = stack.pop()
            if not stack:
                return cls(next, getpath(stack), storage, inputargs)
            stack[-1].append(cls(next, getpath(stack), storage))


    def getlinerange(self):
        if self._linerange is None:
            self._compute_linerange()
        return self._linerange
    linerange = property(getlinerange)

    def getlineset(self):
        if self._lineset is None:
            self._compute_linerange()
        return self._lineset
    lineset = property(getlineset)

    def has_valid_code(self):
        for chunk in self.chunks:
            if not chunk.has_valid_code():
                return False
        return True

    def _compute_linerange(self):
        self._lineset = set()
        minline = sys.maxint
        maxline = -1
        for chunk in self.chunks:
            if chunk.is_bytecode and chunk.filename is not None:
                lineno = chunk.lineno
                minline = min(minline, lineno)
                maxline = max(maxline, lineno)
                if chunk.line_starts_here or len(chunk.operations) > 1:
                    self._lineset.add(lineno)
        if minline == sys.maxint:
            minline = 0
            maxline = 0
        self._linerange = minline, maxline

    def repr(self):
        if self.filename is None:
            return "Unknown"
        return "%s, file '%s', line %d" % (self.name, self.filename,
                                           self.startlineno)

    def __repr__(self):
        return "[%s]" % ", ".join([repr(chunk) for chunk in self.chunks])

    def pretty_print(self, out):
        print >>out, "Loop starting at %s in %s at %d" % (self.name,
                                        self.filename, self.startlineno)
        lineno = -1
        for chunk in self.chunks:
            if chunk.filename is not None and chunk.lineno != lineno:
                lineno = chunk.lineno
                source = chunk.getcode().source[chunk.lineno -
                                                chunk.startlineno]
                print >>out, "  ", source
            chunk.pretty_print(out)


def adjust_bridges(loop, bridges):
    """ Slice given loop according to given bridges to follow. Returns a plain
    list of operations.
    """
    ops = loop.operations
    res = []
    i = 0
    while i < len(ops):
        op = ops[i]
        if op.is_guard() and bridges.get('loop-' + str(op.guard_no), None):
            res.append(op)
            i = 0
            if hasattr(op.bridge, 'force_asm'):
                op.bridge.force_asm()
            ops = op.bridge.operations
        else:
            res.append(op)
            i += 1
    return res


def import_log(logname, ParserCls=SimpleParser):
    log = parse_log_file(logname)
    addrs = {}
    for entry in extract_category(log, 'jit-backend-addr'):
        m = re.search('bootstrap ([-\da-f]+)', entry)
        if not m:
            # a bridge
            m = re.search('has address ([-\da-f]+)', entry)
            addr = int(m.group(1), 16)
            entry = entry.lower()
            m = re.search('guard \d+', entry)
            name = m.group(0)
        else:
            name = entry[:entry.find('(') - 1].lower()
            addr = int(m.group(1), 16)
        addrs.setdefault(addr, []).append(name)
    dumps = {}
    for entry in extract_category(log, 'jit-backend-dump'):
        backend, _, dump, _ = entry.split("\n")
        _, addr, _, data = re.split(" +", dump)
        backend_name = backend.split(" ")[1]
        addr = int(addr[1:], 16)
        if addr in addrs and addrs[addr]:
            name = addrs[addr].pop(0) # they should come in order
            dumps[name] = (backend_name, addr, data)
    loops = []
    for entry in extract_category(log, 'jit-log-opt'):
        parser = ParserCls(entry, None, {}, 'lltype', None,
                           nonstrict=True)
        loop = parser.parse()
        comm = loop.comment
        comm = comm.lower()
        if comm.startswith('# bridge'):
            m = re.search('guard \d+', comm)
            name = m.group(0)
        else:
            name = comm[2:comm.find(':')-1]
        if name in dumps:
            bname, start_ofs, dump = dumps[name]
            loop.force_asm = (lambda dump=dump, start_ofs=start_ofs,
                              bname=bname, loop=loop:
                              parser.postprocess(loop, backend_tp=bname,
                                                 backend_dump=dump,
                                                 dump_start=start_ofs))
        loops.append(loop)
    return log, loops
