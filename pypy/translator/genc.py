"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link, last_exception
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.translator.simplify import remove_direct_loops

# ____________________________________________________________

def uniquemodulename(name, SEEN={}):
    # never reuse the same module name within a Python session!
    i = 0
    while True:
        i += 1
        result = '%s_%d' % (name, i)
        if result not in SEEN:
            SEEN[result] = True
            return result


class GenC:
    MODNAMES = {}

    def __init__(self, f, translator, modname=None):
        self.f = f
        self.translator = translator
        self.modname = (modname or
                        uniquemodulename(translator.functions[0].__name__))
        self.cnames = {Constant(None).key:  'Py_None',
                       Constant(False).key: 'Py_False',
                       Constant(True).key:  'Py_True',
                       }
        self.seennames = {}
        self.initcode = []     # list of lines for the module's initxxx()
        self.latercode = []    # list of generators generating extra lines
                               #   for later in initxxx() -- for recursive
                               #   objects
        self.globaldecl = []
        self.pendingfunctions = []
        self.gen_source()

    def nameof(self, obj):
        key = Constant(obj).key
        try:
            return self.cnames[key]
        except KeyError:
            if type(obj).__module__ != '__builtin__':
                # assume it's a user defined thingy
                name = self.nameof_instance(obj)
            else:
                for cls in type(obj).__mro__:
                    meth = getattr(self,
                                   'nameof_' + cls.__name__.replace(' ', ''),
                                   None)
                    if meth:
                        break
                else:
                    raise TypeError, "nameof(%r)" % (obj,)
                name = meth(obj)
            self.cnames[key] = name
            return name

    def uniquename(self, basename):
        name = basename
        i = 0
        while name in self.seennames:
            i += 1
            name = '%s_%d' % (basename, i)
        self.seennames[name] = True
        return name

    def nameof_int(self, value):
        if value >= 0:
            name = 'gint_%d' % value
        else:
            name = 'gint_minus%d' % abs(value)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = '
                             'PyInt_FromLong(%d))' % (name, value))
        return name

    def nameof_str(self, value):
        chrs = [c for c in value if ('a' <= c <='z' or
                                     'A' <= c <='Z' or
                                     '0' <= c <='9' or
                                     '_' == c )]
        name = self.uniquename('gstr_' + ''.join(chrs))
        self.globaldecl.append('static PyObject* %s;' % name)
        if [c for c in value if not (' '<=c<='~')]:
            # non-printable string
            s = 'chr_%s' % name
            self.globaldecl.append('static char %s[] = { %s };' % (
                s, ', '.join(['%d' % ord(c) for c in value])))
        else:
            # printable string
            s = '"%s"' % value
        self.initcode.append('INITCHK(%s = PyString_FromStringAndSize('
                             '%s, %d))' % (name, s, len(value)))
        return name

    def nameof_function(self, func):
        name = self.uniquename('gfunc_' + func.__name__)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = PyCFunction_New('
                             '&ml_%s, NULL))' % (name, name))
        self.initcode.append('\t%s->ob_type = &PyGenCFunction_Type;' % name)
        self.pendingfunctions.append(func)
        return name

    def nameof_instancemethod(self, meth):
        if meth.im_self is None:
            # no error checking here
            return self.nameof(meth.im_func)
        else:
            ob = self.nameof(meth.im_self)
            func = self.nameof(meth.im_func)
            typ = self.nameof(meth.im_class)
            us = self.uniquename('gmeth_'+meth.im_func.__name__)
            self.globaldecl.append('static PyObject* %s;'%(us,))
            self.initcode.append(
                'INITCHK(%s = gencfunc_descr_get(%s, %s, %s))'%(
                us, func, ob, typ))
            return us
                                   
    def nameof_instance(self, instance):
        name = self.uniquename('ginst_' + instance.__class__.__name__)
        cls = self.nameof(instance.__class__)
        def initinstance():
            content = instance.__dict__.items()
            content.sort()
            for key, value in content:
                yield 'INITCHK(SETUP_INSTANCE_ATTR(%s, "%s", %s))' % (
                    name, key, self.nameof(value))
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(SETUP_INSTANCE(%s, %s))' % (
            name, cls))
        self.latercode.append(initinstance())
        return name

    def nameof_builtin_function_or_method(self, func):
        import __builtin__
        assert func is getattr(__builtin__, func.__name__, None), (
            '%r is not from __builtin__' % (func,))
        name = self.uniquename('gbltin_' + func.__name__)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = PyMapping_GetItemString('
                             'PyEval_GetBuiltins(), "%s"))' % (
            name, func.__name__))
        return name

    def nameof_classobj(self, cls):
        name = self.uniquename('gcls_' + cls.__name__)
        bases = [base for base in cls.__bases__ if base is not object]
        assert len(bases) <= 1, "%r needs multiple inheritance" % (cls,)
        if bases:
            base = bases[0]
        else:
            base = object
        base = self.nameof(base)
        def initclassobj():
            content = cls.__dict__.items()
            content.sort()
            for key, value in content:
                if key.startswith('__') and key != '__init__':
                    if key in ['__module__', '__doc__', '__dict__',
                               '__weakref__', '__repr__']:
                        continue
                    # XXX some __NAMES__ are important... nicer solution sought
                    #raise Exception, "unexpected name %r in class %s"%(key, cls)
                yield 'INITCHK(SETUP_CLASS_ATTR(%s, "%s", %s))' % (
                    name, key, self.nameof(value))
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(SETUP_CLASS(%s, "%s", %s))' % (
            name, cls.__name__, base))
        self.latercode.append(initclassobj())
        return name

    nameof_class = nameof_classobj   # for Python 2.2

    typename_mapping = {
        object: 'PyBaseObject_Type',
        int:    'PyInt_Type',
        long:   'PyLong_Type',
        bool:   'PyBool_Type',
        list:   'PyList_Type',
        tuple:  'PyTuple_Type',
        dict:   'PyDict_Type',
        str:    'PyString_Type',
        }

    def nameof_type(self, cls):
        if cls in self.typename_mapping:
            return '(PyObject*) &%s' % self.typename_mapping[cls]
        assert hasattr(cls, '__weakref__'), (
            "built-in class %r not found in typename_mapping" % (cls,))
        return self.nameof_classobj(cls)

    def nameof_tuple(self, tup):
        name = self.uniquename('g%dtuple' % len(tup))
        def inittuple():
            for i in range(len(tup)):
                item = self.nameof(tup[i])
                yield '\tPy_INCREF(%s);' % item
                yield '\tPyTuple_SET_ITEM(%s, %d, %s);' % (name, i, item)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = PyTuple_New(%d))' % (name, len(tup)))
        self.latercode.append(inittuple())
        return name

    def nameof_list(self, lis):
        name = self.uniquename('g%dlist' % len(lis))
        def initlist():
            for i in range(len(lis)):
                item = self.nameof(lis[i])
                yield '\tPy_INCREF(%s);' % item
                yield '\tPyList_SET_ITEM(%s, %d, %s);' % (name, i, item)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = PyList_New(%d))' % (name, len(lis)))
        self.latercode.append(initlist())
        return name

    def nameof_dict(self, dic):
        name = self.uniquename('g%ddict' % len(dic))
        def initdict():
            for k in dic:
                assert type(k) is str, "can only dump dicts with string keys"
                yield '\tINITCHK(PyDict_SetItemString(%s, "%s", %s) >= 0)'%(
                    name, k, self.nameof(dic[k]))
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('INITCHK(%s = PyDict_New())' % (name,))
        self.latercode.append(initdict())
        return name
            

    def gen_source(self):
        f = self.f
        info = {
            'modname': self.modname,
            'entrypointname': self.translator.functions[0].__name__,
            'entrypoint': self.nameof(self.translator.functions[0]),
            }
        # header
        print >> f, self.C_HEADER

        # function implementations
        while self.pendingfunctions:
            func = self.pendingfunctions.pop(0)
            self.gen_cfunction(func)
            # collect more of the latercode after each function
            while self.latercode:
                gen = self.latercode.pop(0)
                self.initcode.extend(gen)
            self.gen_global_declarations()

        # footer
        print >> f, self.C_INIT_HEADER % info
        for codeline in self.initcode:
            print >> f, '\t' + codeline
        print >> f, self.C_INIT_FOOTER % info

    def gen_global_declarations(self):
        g = self.globaldecl
        if g:
            f = self.f
            print >> f, '/* global declaration%s */' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]

    def gen_cfunction(self, func):
        f = self.f
        body = list(self.cfunction_body(func))
        self.gen_global_declarations()

        # print header
        name = self.nameof(func)
        assert name.startswith('gfunc_')
        f_name = 'f_' + name[6:]
        print >> f, 'static PyObject* %s(PyObject* self, PyObject* args)' % (
            f_name,)
        print >> f, '{'

        # collect and print all the local variables
        graph = self.translator.getflowgraph(func)
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        for a in uniqueitems(localslst):
            print >> f, '\tPyObject* %s;' % a.name
        print >> f

        # argument unpacking
        lst = ['args',
               '"%s"' % func.__name__,
               '%d' % len(graph.getargs()),
               '%d' % len(graph.getargs()),
               ]
        lst += ['&' + a.name for a in graph.getargs()]
        print >> f, '\tif (!PyArg_UnpackTuple(%s))' % ', '.join(lst)
        print >> f, '\t\treturn NULL;'

        # print the body
        for line in body:
            if line.endswith(':'):
                if line.startswith('err'):
                    fmt = '\t%s'
                else:
                    fmt = '    %s\n'
            elif line:
                fmt = '\t%s\n'
            else:
                fmt = '%s\n'
            f.write(fmt % line)
        print >> f, '}'

        # print the PyMethodDef
        print >> f, 'static PyMethodDef ml_%s = { "%s", %s, METH_VARARGS };' % (
            name, func.__name__, f_name)
        print >> f

    def cfunction_body(self, func):
        graph = self.translator.getflowgraph(func)
        remove_direct_loops(graph)
        checkgraph(graph)

        blocknum = {}
        allblocks = []

        def expr(v):
            if isinstance(v, Variable):
                return v.name
            elif isinstance(v, Constant):
                return self.nameof(v.value)
            else:
                raise TypeError, "expr(%r)" % (v,)

        def gen_link(link):
            "Generate the code to jump across the given Link."
            has_ref = {}
            for v in to_release:
                has_ref[v] = True
            for a1, a2 in zip(link.args, link.target.inputargs):
                line = 'MOVE(%s, %s)' % (expr(a1), a2.name)
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    line += '\tPy_INCREF(%s);' % a2.name
                yield line
            for v in to_release:
                if v in has_ref:
                    yield 'Py_DECREF(%s);' % v.name
            yield 'goto block%d;' % blocknum[link.target]

        # collect all blocks
        def visit(block):
            if isinstance(block, Block):
                allblocks.append(block)
                blocknum[block] = len(blocknum)
        traverse(visit, graph)

        # generate an incref for each input argument
        for v in graph.getargs():
            yield 'Py_INCREF(%s);' % v.name

        # generate the body of each block
        for block in allblocks:
            yield ''
            yield 'block%d:' % blocknum[block]
            to_release = list(block.inputargs)
            for op in block.operations:
                lst = [expr(v) for v in op.args]
                lst.append(op.result.name)
                lst.append('err%d_%d' % (blocknum[block], len(to_release)))
                macro = 'OP_%s' % op.opname.upper()
                meth = getattr(self, macro, None)
                if meth:
                    yield meth(lst[:-2], lst[-2], lst[-1])
                else:
                    yield '%s(%s)' % (macro, ', '.join(lst))
                to_release.append(op.result)

            err_reachable = False
            if len(block.exits) == 0:
                retval = expr(block.inputargs[0])
                if hasattr(block, 'exc_type'):
                    # exceptional return block
                    yield 'PyErr_SetObject(PyExc_%s, %s);' % (
                        block.exc_type.__name__, retval)
                    yield 'return NULL;'
                else:
                    # regular return block
                    yield 'return %s;' % retval
                continue
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in gen_link(block.exits[0]):
                    yield op
                yield ''
            elif block.exitswitch == Constant(last_exception):
                # block catching the exceptions raised by its last operation
                # we handle the non-exceptional case first
                link = block.exits[0]
                assert link.exitcase is None
                for op in gen_link(link):
                    yield op
                # we must catch the exception raised by the last operation,
                # which goes to the last err%d_%d label written above.
                yield ''
                to_release.pop()  # skip default error handling for this label
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                yield ''
                for link in block.exits[1:]:
                    assert issubclass(link.exitcase, Exception)
                    yield 'if (PyErr_ExceptionMatches(PyExc_%s)) {' % (
                        link.exitcase.__name__,)
                    yield '\tPyErr_Clear();'
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                err_reachable = True
            else:
                # block ending in a switch on a value
                for link in block.exits[:-1]:
                    yield 'if (EQ_%s(%s)) {' % (link.exitcase,
                                                block.exitswitch.name)
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                link = block.exits[-1]
                yield 'assert(EQ_%s(%s));' % (link.exitcase,
                                              block.exitswitch.name)
                for op in gen_link(block.exits[-1]):
                    yield op
                yield ''

            while to_release:
                v = to_release.pop()
                if err_reachable:
                    yield 'Py_DECREF(%s);' % v.name
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield 'return NULL;'

# ____________________________________________________________

    C_HEADER = open(os.path.join(autopath.this_dir, 'genc.h')).read()

    C_SEP = "/************************************************************/"

    C_INIT_HEADER = C_SEP + '''

static PyMethodDef no_methods[] = { NULL, NULL };
void init%(modname)s(void)
{
\tPyObject* m = Py_InitModule("%(modname)s", no_methods);
\tSETUP_MODULE
'''

    C_INIT_FOOTER = '''
\tPyModule_AddObject(m, "%(entrypointname)s", %(entrypoint)s);
}'''

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, args, r, err):
        if len(args) == 0:
            return 'OP_NEWLIST0(%s, %s)' % (r, err)
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWTUPLE(self, args, r, err):
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_SIMPLE_CALL(self, args, r, err):
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s, %s)' % (', '.join(args), r, err)

# ____________________________________________________________

def cdecl(type, name):
    # Utility to generate a typed name declaration in C syntax.
    # For local variables, struct fields, function declarations, etc.
    # For complex C types, the 'type' can contain a '@' character that
    # specifies where the 'name' should be inserted; for example, an
    # array of 10 ints has a type of "int @[10]".
    if '@' in type:
        return type.replace('@', name)
    else:
        return ('%s %s' % (type, name)).rstrip()
