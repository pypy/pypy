import re, sys
from lib_pypy.disassembler import dis
from pypy.jit.metainterp.resoperation import rop, opname
from pypy.jit.tool.oparser import OpParser

class Html(str):
    def __html__(self):
        return self

    def plaintext(self):
        # This is not a general way to strip tags, but it's good enough to use
        # in tests
        import re
        s = re.sub('<.*?>', '', self)
        s = s.replace("&lt;", "<")
        s = s.replace("&gt;", ">")
        s = s.replace("&amp;", "&")
        return s


def cssclass(cls, s, **kwds):
    attrs = ['%s="%s"' % (name, value) for name, value in kwds.iteritems()]
    return '<span class="%s" %s>%s</span>' % (cls, ' '.join(attrs), s)


def _new_binop(name):
    import cgi
    name = cgi.escape(name)
    def f(self):
        return '%s = %s %s %s' % (self.getres(), self.getarg(0), name, self.getarg(1))
    return f

class Op(object):
    bridge = None
    
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

    def html_repr(self):
        s = getattr(self, 'repr_' + self.name, self.generic_repr)()
        if self.is_guard():
            s = '<span class="guard">guard</span>(' + s + ')'
        return Html(s)

    def getarg(self, i):
        return self._getvar(self.args[i])

    def getargs(self):
        return [self._getvar(v) for v in self.args]

    def getres(self):
        return self._getvar(self.res)

    def _getvar(self, v):
        return cssclass(v, v, onmouseover='highlight_var(this)', onmouseout='disable_var(this)')

    def is_guard(self):
        return self._is_guard

    for bin_op, name in [('==', 'int_eq'),
                         ('!=', 'int_ne'),
                         ('==', 'float_eq'),
                         ('!=', 'float_ne'),
                         ('>', 'int_gt'),
                         ('<', 'int_lt'),
                         ('<=', 'int_le'),
                         ('>=', 'int_ge'),
                         ('+', 'int_add'),
                         ('+', 'float_add'),
                         ('-', 'int_sub'),
                         ('-', 'float_sub'),
                         ('*', 'int_mul'),
                         ('*', 'float_mul'),
                         ('&', 'int_and')]:
        locals()['repr_' + name] = _new_binop(bin_op)

    def repr_guard_true(self):
        return '%s is true' % self.getarg(0)

    def repr_guard_false(self):
        return '%s is false' % self.getarg(0)

    def repr_guard_value(self):
        return '%s is %s' % (self.getarg(0), self.getarg(1))

    def repr_guard_isnull(self):
        return '%s is null' % self.getarg(0)

    def repr_getfield_raw(self):
        name, field = self.descr.split(' ')[1].rsplit('.', 1)
        return '%s = ((%s)%s).%s' % (self.getres(), name, self.getarg(0), field[2:])

    def repr_getfield_gc(self):
        fullname, field = self.descr.split(' ')[1].rsplit('.', 1)
        names = fullname.rsplit('.', 1)
        if len(names) == 2:
            namespace, classname = names
        else:
            namespace = ''
            classname = names[0]
        namespace = cssclass('namespace', namespace)
        classname = cssclass('classname', classname)
        field = cssclass('fieldname', field)
            
        obj = self.getarg(0)
        return '%s = ((%s.%s)%s).%s' % (self.getres(), namespace, classname, obj, field)
    repr_getfield_gc_pure = repr_getfield_gc

    def repr_setfield_raw(self):
        name, field = self.descr.split(' ')[1].rsplit('.', 1)
        return '((%s)%s).%s = %s' % (name, self.getarg(0), field[2:], self.getarg(1))

    def repr_setfield_gc(self):
        name, field = self.descr.split(' ')[1].rsplit('.', 1)
        return '((%s)%s).%s = %s' % (name, self.getarg(0), field, self.getarg(1))

    def generic_repr(self):
        arglist = ', '.join(self.getargs())
        if self.res is not None:
            return '%s = %s(%s)' % (self.getres(), self.name, arglist)
        else:
            return '%s(%s)' % (self.name, arglist)

    def __repr__(self):
        return '<%s (%s)>' % (self.name, ', '.join([repr(a)
                                                    for a in self.args]))

class SimpleParser(OpParser):
    def parse_args(self, opname, argspec):
        if not argspec.strip():
            return [], None
        if opname == 'debug_merge_point':
            return argspec.rsplit(", ", 1), None
        else:
            args = argspec.split(', ')
            descr = None
            if args[-1].startswith('descr='):
                descr = args[-1][len('descr='):]
                args = args[:-1]
            return (args, descr)

    def box_for_var(self, res):
        return res

    def create_op(self, opnum, args, res, descr):
        return Op(intern(opname[opnum].lower()), args, res, descr)

class NonCodeError(Exception):
    pass

class Bytecode(object):
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
            self.inline_level = int(operations[0].args[1])
            m = re.search('<code object ([<>\w]+), file \'(.+?)\', line (\d+)> #(\d+) (\w+)',
                         operations[0].getarg(0))
            if m is None:
                # a non-code loop, like StrLiteralSearch or something
                self.bytecode_name = operations[0].args[0].split(" ")[0][1:]
            else:
                self.name, self.filename, lineno, bytecode_no, self.bytecode_name = m.groups()
                self.startlineno = int(lineno)
                self.bytecode_no = int(bytecode_no)
        self.operations = operations
        self.storage = storage

    def repr(self):
        if self.filename is None:
            return "Unknown"
        return "%s, file '%s', line %d" % (self.name, self.filename,
                                           self.startlineno)

    def getcode(self):
        if self.code is None:
            self.code = dis(self.storage.load_code(self.filename)[self.startlineno])
        return self.code

    def getlineno(self):
        code = self.getcode()
        return code.map[self.bytecode_no].lineno
    lineno = property(getlineno)

    def getline_starts_here(self):
        code = self.getcode()
        return code.map[self.bytecode_no].line_starts_here
    line_starts_here = property(getline_starts_here)

    def __repr__(self):
        return "[%s]" % ", ".join([repr(op) for op in self.operations])

    def pretty_print(self, out):
        pass

    def html_repr(self):
        if self.filename is not None:
            code = self.getcode()
            opcode = self.code.map[self.bytecode_no]
            return '%s %s' % (self.bytecode_name, opcode.argstr)
        else:
            return self.bytecode_name

class Function(object):
    filename = None
    name = None
    startlineno = 0
    _linerange = None
    _lineset = None
    is_bytecode = False
    inline_level = None
    
    def __init__(self, chunks, path, storage):
        self.path = path
        self.chunks = chunks
        for chunk in self.chunks:
            if chunk.filename is not None:
                self.startlineno = chunk.startlineno
                self.filename = chunk.filename
                self.name = chunk.name
                self.inline_level = chunk.inline_level
                break
        self.storage = storage

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

    def html_repr(self):
        return "inlined call to %s in %s" % (self.name, self.filename)

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

def parse(input):
    return SimpleParser(input, None, {}, 'lltype', None,
                        nonstrict=True).parse()

def slice_debug_merge_points(operations, storage, limit=None):
    """ Slice given operation list into a chain of Bytecode chunks.
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
                    stack[-1].append(Function(last, getpath(stack), storage))
                else:
                    stack.append([])
        stack[-1].append(bc)

    so_far = []
    stack = []
    for op in operations:
        if op.name == 'debug_merge_point':
            if so_far:
                append_to_res(Bytecode(so_far, storage))
                if limit:
                    break
                so_far = []
        so_far.append(op)
    if so_far:
        append_to_res(Bytecode(so_far, storage))
    # wrap stack back up
    if not stack:
        # no ops whatsoever
        return Function([], getpath(stack), storage)
    while True:
        next = stack.pop()
        if not stack:
            return Function(next, getpath(stack), storage)
        stack[-1].append(Function(next, getpath(stack), storage))

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
            ops = op.bridge.operations
        else:
            res.append(op)
            i += 1
    return res
