from __future__ import generators
from pypy.objspace.flow.model import Variable, Constant
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.objspace.flow.model import Block, Link
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.translator.unsimplify import remove_direct_loops
from pypy.interpreter.pycode import CO_VARARGS
from types import FunctionType

from pypy.translator.gensupp import c_string
from pypy.translator.genc_pyobj import ctypeof

# Set this if you want call trace frames to be built
USE_CALL_TRACE = False


class FunctionDef:
    """
    Collects information about a function which we have to generate.
    The operations of each function are collected in a C function
    with signature:

        static T fn_xxx(T1 arg1, T2 arg2, etc);

    where the T, T1, T2.. are C types like 'int' or 'PyObject *'.

    If needed, another wrapper function is created with a signature
    suitable for the built-in function type of CPython:

        static PyObject *pyfn_xxx(PyObject *self, PyObject *args, PyObject* kw);

    The built-in function object, if needed, is put in the global
    variable named gfn_xxx.
    """

    def __init__(self, func, genc):
        self.func = func
        self.genc = genc

        # get the function name
        namespace = genc.namespace
        self.fast_name = namespace.uniquename('fn_' + func.__name__) # fn_xxx
        self.base_name = self.fast_name[3:]                          # xxx
        self.wrapper_name = None                                     # pyfn_xxx
        self.globalobject_name = None                                # gfunc_xxx
        self.localscope = namespace.localScope()

        # get the flow graph, and ensure that there is no direct loop in it
        # as we cannot generate valid code for this case.
        self.graph = graph = genc.translator.getflowgraph(func)
        remove_direct_loops(genc.translator, graph)
        checkgraph(graph)
        graph_args = graph.getargs()

        # collect all the local variables
        localslst = []
        def visit(node):
            if isinstance(node, Block):
                localslst.extend(node.getvariables())
        traverse(visit, graph)
        fast_set = dict(zip(graph_args, graph_args))
        self.localnames = [self.decl(a) for a in localslst if a not in fast_set]

        # collect all the arguments
        fast_args         = [self.expr(a) for a in graph_args]
        declare_fast_args = [self.decl(a) for a in graph_args]
        if USE_CALL_TRACE:
            declare_fast_args.insert(0, 'TRACE_ARGS')
        declare_fast_args = ', '.join(declare_fast_args) or 'void'
        name_and_arguments = '%s(%s)' % (self.fast_name, declare_fast_args)
        ctret = ctypeof(graph.getreturnvar())
        fast_function_header = 'static ' + (
            ctret.ctypetemplate % (name_and_arguments,))

        name_of_defaults = [self.genc.pyobjrepr.nameof(x, debug=('Default argument of',
                                                       self))
                            for x in (func.func_defaults or ())]

        # store misc. information
        self.fast_function_header = fast_function_header
        self.graphargs = graph_args
        self.ctret = ctret
        self.vararg = bool(func.func_code.co_flags & CO_VARARGS)
        self.fast_args = fast_args
        self.name_of_defaults = name_of_defaults
        
        error_return = getattr(ctret, 'error_return', 'NULL')
        self.return_error = 'FUNCTION_RETURN(%s)' % error_return

        # generate the forward header
        self.genc.globaldecl.append(fast_function_header + ';  /* forward */')


    def get_globalobject(self):
        if self.globalobject_name is None:
            self.wrapper_name = 'py' + self.fast_name
            self.globalobject_name = self.genc.pyobjrepr.uniquename('gfunc_' +
                                                          self.base_name)
        return self.globalobject_name

    def clear(self):
        del self.localscope
        del self.localnames
        del self.graph

    def decl(self, v):
        assert isinstance(v, Variable)
        return ctypeof(v).ctypetemplate % (self.localscope.localname(v.name),)

    def expr(self, v):
        if isinstance(v, Variable):
            return self.localscope.localname(v.name)
        elif isinstance(v, Constant):
            return self.genc.nameofconst(v,
                                    debug=('Constant in the graph of', self))
        else:
            raise TypeError, "expr(%r)" % (v,)

    # ____________________________________________________________

    def gen_wrapper(self, f):
        func             = self.func
        f_name           = self.wrapper_name
        name_of_defaults = self.name_of_defaults
        graphargs        = self.graphargs
        vararg           = self.vararg
        nb_positional_args = len(graphargs) - vararg

        min_number_of_args = nb_positional_args - len(name_of_defaults)
        print >> f, 'static PyObject *'
        print >> f, '%s(PyObject* self, PyObject* args, PyObject* kwds)' % (
            f_name,)
        print >> f, '{'
        if USE_CALL_TRACE:
            print >> f, '\tFUNCTION_HEAD(%s, %s, args, %s, __FILE__, __LINE__ - 2)' % (
                c_string('%s(%s)' % (self.base_name, ', '.join(name_of_defaults))),
                self.globalobject_name,
                '(%s)' % (', '.join(map(c_string, name_of_defaults) + ['NULL']),),
            )

        kwlist = ['"%s"' % name for name in
                      func.func_code.co_varnames[:func.func_code.co_argcount]]
        kwlist.append('0')
        print >> f, '\tstatic char* kwlist[] = {%s};' % (', '.join(kwlist),)

        numberednames = ['o%d' % (i+1) for i in range(len(graphargs))]
        if vararg:
            numberednames[-1] = 'ovararg'
        numberednames.append('oret')
        print >> f, '\tPyObject *%s;' % (', *'.join(numberednames))
        conversions = []
        call_fast_args = []
        for a, numberedname in zip(graphargs, numberednames):
            try:
                convert_from_obj = a.type_cls.convert_from_obj
            except AttributeError:
                call_fast_args.append(numberedname)
            else:
                convertedname = numberedname.replace('o', 'a')
                ct = ctypeof(a)
                print >> f, '\t%s;' % (ct.ctypetemplate % (convertedname,))
                conversions.append('\tOP_%s(%s, %s, type_error)' % (
                    convert_from_obj.upper(), numberedname, convertedname))
                # XXX successfully converted objects may need to be decrefed
                # XXX even though they are not PyObjects
                call_fast_args.append(convertedname)
        # return value conversion
        try:
            convert_to_obj = self.ctret.convert_to_obj
        except AttributeError:
            putresultin = 'oret'
            footer = None
        else:
            print >> f, '\t%s;' % (self.ctret.ctypetemplate % ('aret',))
            putresultin = 'aret'
            footer = 'OP_%s(aret, oret, type_error)' % convert_to_obj.upper()
        print >> f

        if USE_CALL_TRACE:
            print >> f, '\tFUNCTION_CHECK()'

        # argument unpacking
        if vararg:
            print >> f, '\tovararg = PyTuple_GetSlice(args, %d, INT_MAX);' % (
                nb_positional_args,)
            print >> f, '\tif (ovararg == NULL)'
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\targs = PyTuple_GetSlice(args, 0, %d);' % (
                nb_positional_args,)
            print >> f, '\tif (args == NULL) {'
            print >> f, '\t\tERR_DECREF(ovararg)'
            print >> f, '\t\tFUNCTION_RETURN(NULL)'
            print >> f, '\t}'
            tail = """{
\t\tERR_DECREF(args)
\t\tERR_DECREF(ovararg)
\t\tFUNCTION_RETURN(NULL);
\t}
\tPy_DECREF(args);"""
        else:
            tail = '\n\t\tFUNCTION_RETURN(NULL)'
        for i in range(len(name_of_defaults)):
            print >> f, '\t%s = %s;' % (
                numberednames[min_number_of_args+i],
                name_of_defaults[i])
        fmt = 'O'*min_number_of_args
        if min_number_of_args < nb_positional_args:
            fmt += '|' + 'O'*(nb_positional_args-min_number_of_args)
        lst = ['args', 'kwds',
               '"%s:%s"' % (fmt, func.__name__),
               'kwlist',
               ]
        lst += ['&' + a for a in numberednames]
        print >> f, '\tif (!PyArg_ParseTupleAndKeywords(%s))' % ', '.join(lst),
        print >> f, tail

        for line in conversions:
            print >> f, line

        if USE_CALL_TRACE:
            call_fast_args.insert(0, 'TRACE_CALL')
        call_fast_args = ', '.join(call_fast_args)
        print >> f, '\t%s = %s(%s);' % (putresultin, self.fast_name,
                                        call_fast_args)
        if footer:
            print >> f, '\t' + footer
        print >> f, '\treturn oret;'

        if conversions or footer:
            print >> f, '    type_error:'
            print >> f, '        return NULL;'
        
        print >> f, '}'
        print >> f

    # ____________________________________________________________

    def gen_cfunction(self, f, body):
        print >> f, self.fast_function_header
        print >> f, '{'

        localnames = self.localnames
        lengths = [len(a) for a in localnames]
        lengths.append(9999)
        start = 0
        while start < len(localnames):
            total = lengths[start] + 9
            end = start+1
            while total + lengths[end] < 76:
                total += lengths[end] + 2
                end += 1
            print >> f, '\t' + '; '.join(localnames[start:end]) + ';'
            start = end
        
        # generate an incref for each input argument
        for a in self.graphargs:
            cincref = getattr(ctypeof(a), 'cincref', None)
            if cincref:
                print >> f, '\t' + cincref % (self.expr(a),)

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
        print >> f

    # ____________________________________________________________

    def cfunction_body(self):
        graph = self.graph

        blocknum = {}
        allblocks = []

        def gen_link(link, linklocalvars=None):
            "Generate the code to jump across the given Link."
            has_ref = {}
            linklocalvars = linklocalvars or {}
            for v in to_release:
                linklocalvars[v] = self.expr(v)
            has_ref = linklocalvars.copy()
            for a1, a2 in zip(link.args, link.target.inputargs):
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = self.expr(a1)
                line = 'MOVE(%s, %s)' % (src, self.expr(a2))
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    ct1 = ctypeof(a1)
                    ct2 = ctypeof(a2)
                    assert ct1 == ct2
                    cincref = getattr(ct1, 'cincref', None)
                    if cincref:
                        line += '\t' + cincref % (self.expr(a2),)
                yield line
            for v in has_ref:
                cdecref = getattr(ctypeof(v), 'cdecref', None)
                if cdecref:
                    yield cdecref % (linklocalvars[v],)
            yield 'goto block%d;' % blocknum[link.target]

        # collect all blocks
        def visit(block):
            if isinstance(block, Block):
                allblocks.append(block)
                blocknum[block] = len(blocknum)
        traverse(visit, graph)

        # generate the body of each block
        for block in allblocks:
            yield ''
            yield 'block%d:' % blocknum[block]
            to_release = list(block.inputargs)
            for op in block.operations:
                args  = [lazy(self.expr, v) for v in op.args]
                res   = self.expr(op.result)
                err   = 'err%d_%d' % (blocknum[block], len(to_release))
                macro = 'OP_%s' % op.opname.upper()
                meth  = getattr(self, macro, None)
                if meth:
                    yield meth(args, res, err)
                else:
                    lst = [arg.compute() for arg in args] + [res, err]
                    yield '%s(%s)' % (macro, ', '.join(lst))
                to_release.append(op.result)

            err_reachable = False
            if len(block.exits) == 0:
                if len(block.inputargs) == 2:   # exc_cls, exc_value
                    # exceptional return block
                    exc_cls   = self.expr(block.inputargs[0])
                    exc_value = self.expr(block.inputargs[1])
                    yield 'PyErr_Restore(%s, %s, NULL);' % (exc_cls, exc_value)
                    yield self.return_error
                else:
                    # regular return block
                    retval = self.expr(block.inputargs[0])
                    yield 'FUNCTION_RETURN(%s)' % retval
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
                    yield 'if (PyErr_ExceptionMatches(%s)) {' % (
                        self.genc.pyobjrepr.nameof(link.exitcase),)
                    yield '\tPyObject *exc_cls, *exc_value, *exc_tb;'
                    yield '\tPyErr_Fetch(&exc_cls, &exc_value, &exc_tb);'
                    yield '\tif (exc_value == NULL) {'
                    yield '\t\texc_value = Py_None;'
                    yield '\t\tPy_INCREF(Py_None);'
                    yield '\t}'
                    yield '\tPy_XDECREF(exc_tb);'
                    for op in gen_link(link, {
                                Constant(last_exception): 'exc_cls',
                                Constant(last_exc_value): 'exc_value'}):
                        yield '\t' + op
                    yield '}'
                err_reachable = True
            else:
                # block ending in a switch on a value
                ct = ctypeof(block.exitswitch)
                for link in block.exits[:-1]:
                    assert link.exitcase in (False, True)
                    yield 'if (%s == %s) {' % (self.expr(block.exitswitch),
                                       self.genc.nameofvalue(link.exitcase, ct))
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                link = block.exits[-1]
                assert link.exitcase in (False, True)
                yield 'assert(%s == %s);' % (self.expr(block.exitswitch),
                                       self.genc.nameofvalue(link.exitcase, ct))
                for op in gen_link(block.exits[-1]):
                    yield op
                yield ''

            while to_release:
                v = to_release.pop()
                if err_reachable:
                    if not hasattr(v, 'type_cls'):
                        yield 'ERR_DECREF(%s)' % self.expr(v)
                    else:
                        cdecref = getattr(ctypeof(v), 'cdecref', None)
                        if cdecref:
                            yield cdecref % (self.expr(v),)
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield self.return_error

    # ____________________________________________________________

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, args, r, err):
        args = [arg.compute() for arg in args]
        if len(args) == 0:
            return 'OP_NEWLIST0(%s, %s)' % (r, err)
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWDICT(self, args, r, err):
        args = [arg.compute() for arg in args]
        if len(args) == 0:
            return 'OP_NEWDICT0(%s, %s)' % (r, err)
        else:
            assert len(args) % 2 == 0
            args.insert(0, '%d' % (len(args)//2))
            return 'OP_NEWDICT((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWTUPLE(self, args, r, err):
        args = [arg.compute() for arg in args]
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s, %s)' % (', '.join(args), r, err)

    def fast_simple_call(self, args, r, err):
        # try to generate a SIMPLE_CALL using a shortcut:
        # a direct call to the ff_xxx() function, using its C signature.
        if USE_CALL_TRACE:
            return None
        target = args[0].args[0]
        args = [arg.compute() for arg in args[1:]]
        if not isinstance(target, Constant):
            return None
        if not isinstance(target.value, FunctionType):
            return None
        funcdef = self.genc.getfuncdef(target.value)
        if funcdef is None:
            return None
        if len(funcdef.graphargs) != len(args) or funcdef.vararg:
            return None
        return 'if (!(%s=%s(%s))) FAIL(%s);' % (
            r, funcdef.fast_name, ', '.join(args), err)

    def OP_SIMPLE_CALL(self, args, r, err):
        result = self.fast_simple_call(args, r, err)
        if result is not None:
            return result
        # fall-back
        args = [arg.compute() for arg in args]
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_CALL_ARGS(self, args, r, err):
        args = [arg.compute() for arg in args]
        return 'OP_CALL_ARGS((%s), %s, %s)' % (', '.join(args), r, err)

# ____________________________________________________________

class lazy:
    def __init__(self, fn, *args, **kwds):
        self.fn = fn
        self.args = args
        self.kwds = kwds
    def compute(self):
        return self.fn(*self.args, **self.kwds)
