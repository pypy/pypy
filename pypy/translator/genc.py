"""
Generate a C source file from the flowmodel.

"""
from __future__ import generators
import autopath, os
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import FunctionGraph, Block, Link
from pypy.objspace.flow.model import traverse, uniqueitems

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
        self.cnames = {}
        self.seennames = {}
        self.initcode = []
        self.globaldecl = []
        self.pendingfunctions = []
        self.gen_source()

    def nameof(self, obj):
        key = type(obj), obj   # to avoid confusing e.g. 0 and 0.0
        try:
            return self.cnames[key]
        except KeyError:
            for cls in type(obj).__mro__:
                meth = getattr(self, 'nameof_' + cls.__name__, None)
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
        self.initcode.append('%s = PyInt_FromLong(%d);' % (name, value))
        return name

    def nameof_function(self, func):
        name = self.uniquename('gfunc_' + func.__name__)
        self.globaldecl.append('static PyObject* %s;' % name)
        self.initcode.append('%s = PyCFunction_New(&ml_%s, NULL);' % (name,
                                                                      name))
        self.pendingfunctions.append(func)
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
        for func in self.pendingfunctions:
            self.gen_cfunction(func)

        # footer
        print >> f, self.C_INIT_HEADER % info
        for codeline in self.initcode:
            print >> f, '\t' + codeline
        print >> f, self.C_INIT_FOOTER % info

    def gen_cfunction(self, func):
        f = self.f
        body = list(self.cfunction_body(func))
        g = self.globaldecl
        if g:
            print >> f, '/* global declaration%s */' % ('s'*(len(g)>1))
            for line in g:
                print >> f, line
            print >> f
            del g[:]

        # print header
        name = self.nameof(func)
        assert name.startswith('gfunc_')
        f_name = 'f_' + name[6:]
        print >> f, 'static PyObject* %s(PyObject* self, PyObject* args)' % (
            f_name,)
        print >> f, '{'

        # collect and print all the local variables
        graph = self.translator.flowgraphs[func]
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        for a in uniqueitems(localslst):
            print >> f, '\tPyObject* %s;' % a.name
        print >> f

        # argument unpacking
        lst = ['"' + 'O'*len(graph.getargs()) + '"']
        lst += ['&' + a.name for a in graph.getargs()]
        print >> f, '\tif (!PyArg_ParseTuple(args, %s))' % ', '.join(lst)
        print >> f, '\t\treturn NULL;'

        # print the body
        for line in body:
            if line.endswith(':'):
                line = '    ' + line
            else:
                line = '\t' + line
            print >> f, line
        print >> f, '}'

        # print the PyMethodDef
        print >> f, 'static PyMethodDef ml_%s = { "%s", %s, METH_VARARGS };' % (
            name, func.__name__, f_name)
        print >> f

    def cfunction_body(self, func):
        graph = self.translator.flowgraphs[func]
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
                    yield 'Py_XDECREF(%s);' % v.name
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
                yield 'OP_%s(%s)' % (op.opname.upper(), ', '.join(lst))
                to_release.append(op.result)

            if len(block.exits) == 0:
                yield 'return %s;' % expr(block.inputargs[0])
                continue
            if block.exitswitch is not None:
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
            to_release.pop()  # this label is never reachable
            while to_release:
                n = len(to_release)
                v = to_release.pop()
                yield 'err%d_%d: Py_XDECREF(%s);' % (blocknum[block], n, v.name)
            yield 'return NULL;'

# ____________________________________________________________

    C_HEADER = open(os.path.join(autopath.this_dir, 'genc.h')).read()

    C_SEP = "/************************************************************/"

    C_INIT_HEADER = C_SEP + '''

void init%(modname)s(void)
{
\tPyObject* m = Py_InitModule("%(modname)s", NULL);
'''

    C_INIT_FOOTER = '''
\tPyModule_AddObject(m, "%(entrypointname)s", %(entrypoint)s);
}'''

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
