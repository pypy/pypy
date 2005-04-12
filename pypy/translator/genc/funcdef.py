from __future__ import generators
from pypy.objspace.flow import FlowObjSpace
from pypy.objspace.flow.model import Variable, Constant, SpaceOperation
from pypy.objspace.flow.model import traverse, uniqueitems, checkgraph
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.objspace.flow.model import last_exception, last_exc_value
from pypy.translator.simplify import simplify_graph
from pypy.translator.unsimplify import remove_direct_loops
from pypy.translator.genc.t_simple import CIntType, CNoneType
from pypy.translator.genc.t_func import CFuncPtrType
from pypy.translator.genc.t_pyobj import CBorrowedPyObjectType
from pypy.interpreter.pycode import CO_VARARGS
from pypy.tool.compile import compile2
from types import FunctionType

from pypy.translator.gensupp import c_string

# Set this if you want call trace frames to be built
USE_CALL_TRACE = False
# XXX doesn't work any more because of the way gen_wrapper() works, sorry


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

    def __init__(self, func, genc, graph=None, fast_name=None):
        self.func = func
        self.genc = genc

        # get the function name
        namespace = genc.namespace
        if fast_name is None:
            fast_name  = namespace.uniquename('fn_' + func.__name__) # fn_xxx
        self.fast_name = fast_name
        self.base_name = fast_name[3:]                               # xxx
        self.wrapper_name = None                                     # pyfn_xxx
        self.globalobject_name = None                                # gfunc_xxx
        self.localscope = namespace.localScope()

        # get the flow graph, and ensure that there is no direct loop in it
        # as we cannot generate valid code for this case.
        if graph is None:
            graph = genc.translator.getflowgraph(func)
        self.graph = graph
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
        ctret = self.ctypeof(graph.getreturnvar())
        fast_function_header = 'static ' + (
            ctret.ctypetemplate % (name_and_arguments,))

        # store misc. information
        self.fast_function_header = fast_function_header
        self.graphargs = graph_args
        self.ctret = ctret
        self.vararg = bool(func.func_code.co_flags & CO_VARARGS)
        self.fast_args = fast_args
        self.func_defaults = func.func_defaults or ()
        
        error_return = getattr(ctret, 'error_return', 'NULL')
        self.return_error = 'FUNCTION_RETURN(%s)' % error_return

        # generate the forward header
        self.genc.globaldecl.append(fast_function_header + ';  /* forward */')


    def ctypeof(self, var_or_const):
        try:
            return var_or_const.concretetype
        except AttributeError:
            return self.genc.pyobjtype

    def get_globalobject(self):
        if self.globalobject_name is None:
            self.wrapper_name = 'py' + self.fast_name
            self.globalobject_name = self.genc.pyobjtype.uniquename('gfunc_' +
                                                          self.base_name)
        return self.globalobject_name

    def clear(self):
        del self.localscope
        del self.localnames
        del self.graph

    def decl(self, v):
        assert isinstance(v, Variable)
        ct = self.ctypeof(v)
        return ct.ctypetemplate % (self.localscope.localname(v.name),)

    def expr(self, v):
        if isinstance(v, Variable):
            return self.localscope.localname(v.name)
        elif isinstance(v, Constant):
            return self.genc.nameofconst(v,
                                    debug=('Constant in the graph of', self))
        else:
            raise TypeError, "expr(%r)" % (v,)

    # ____________________________________________________________

    def gen_wrapper(self):
        # the wrapper is the function that takes the CPython signature
        #
        #    PyObject *fn(PyObject *self, PyObject *args, PyObject *kwds)
        #
        # and decodes the arguments and calls the "real" C function.
        # We generate the wrapper itself as a Python function which is
        # turned into C.  This makes gen_wrapper() more or less clean.
        #

        TPyObject = self.genc.pyobjtype
        TInt      = self.genc.translator.getconcretetype(CIntType)
        TNone     = self.genc.translator.getconcretetype(CNoneType)
        TBorrowed = self.genc.translator.getconcretetype(CBorrowedPyObjectType)
        args_ct   = [self.ctypeof(a) for a in self.graphargs]
        res_ct    = self.ctret
        nb_positional_args = len(self.graphargs) - self.vararg

        # "def wrapper(self, args, kwds)"
        vself = Variable('self')
        vargs = Variable('args')
        vkwds = Variable('kwds')
        block = Block([vself, vargs, vkwds])
        vfname = Constant(self.base_name)

        # avoid incref/decref on the arguments: 'self' and 'kwds' can be NULL
        vself.concretetype = TBorrowed
        vargs.concretetype = TBorrowed
        vkwds.concretetype = TBorrowed

        # "argument_i = decode_arg(fname, pos, name, vargs, vkwds)"  or
        # "argument_i = decode_arg_def(fname, pos, name, vargs, vkwds, default)"
        varguments = []
        varnames = self.func.func_code.co_varnames
        for i in range(nb_positional_args):
            opargs = [vfname, Constant(i),
                      Constant(varnames[i]), vargs, vkwds]
            opargs[1].concretetype = TInt
            try:
                default_value = self.func_defaults[i - nb_positional_args]
            except IndexError:
                opname = 'decode_arg'
            else:
                opname = 'decode_arg_def'
                opargs.append(Constant(default_value))
            v = Variable('a%d' % i)
            block.operations.append(SpaceOperation(opname, opargs, v))
            varguments.append(v)

        if self.vararg:
            # "vararg = vargs[n:]"
            vararg = Variable('vararg')
            opargs = [vargs, Constant(nb_positional_args), Constant(None)]
            block.operations.append(SpaceOperation('getslice', opargs, vararg))
            varguments.append(vararg)
        else:
            # "check_no_more_arg(fname, n, vargs)"
            vnone = Variable()
            vnone.concretetype = TNone
            opargs = [vfname, Constant(nb_positional_args), vargs]
            opargs[1].concretetype = TInt
            block.operations.append(SpaceOperation('check_no_more_arg',
                                                   opargs, vnone))

        if self.genc.translator.annotator is not None:
            # "argument_i = type_conversion_operations(argument_i)"
            from pypy.translator.genc.ctyper import GenCSpecializer
            from pypy.translator.typer import flatten_ops
            typer = GenCSpecializer(self.genc.translator.annotator)

            assert len(varguments) == len(self.graphargs)
            for i in range(len(varguments)):
                varguments[i].concretetype = TPyObject
                varguments[i], convops = typer.convertvar(varguments[i],
                                                          args_ct[i])
                flatten_ops(convops, block.operations)
        else:
            typer = None

        # "result = direct_call(func, argument_0, argument_1, ..)"
        opargs = [Constant(self.func)] + varguments
        opargs[0].concretetype = self.genc.translator.getconcretetype(
            CFuncPtrType, tuple(args_ct), res_ct)
        vresult = Variable('result')
        block.operations.append(SpaceOperation('direct_call', opargs, vresult))

        if typer is not None:
            # "result2 = type_conversion_operations(result)"
            vresult.concretetype = res_ct
            vresult, convops = typer.convertvar(vresult, TPyObject)
            flatten_ops(convops, block.operations)

        # "return result"
        wgraph = FunctionGraph(self.wrapper_name, block)
        block.closeblock(Link([vresult], wgraph.returnblock))
        checkgraph(wgraph)

        # generate the C source of this wrapper function
        wfuncdef = FunctionDef(dummy_wrapper, self.genc,
                               wgraph, self.wrapper_name)
        self.genc.gen_cfunction(wfuncdef)


    def DISABLED_OLD_gen_wrapper(self, f):
        # XXX this is a huge mess.  Think about producing the wrapper by
        #     generating its content as a flow graph...
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
            ct = self.ctypeof(a)
            if ct == self.genc.pyobjtype:
                call_fast_args.append(numberedname)
            else:
                convert_from_obj = ct.opname_conv_from_obj  # simple conv only!
                convertedname = numberedname.replace('o', 'a')
                print >> f, '\t%s;' % (ct.ctypetemplate % (convertedname,))
                conversions.append('\tOP_%s(%s, %s, type_error)' % (
                    convert_from_obj.upper(), numberedname, convertedname))
                # XXX successfully converted objects may need to be decrefed
                # XXX even though they are not PyObjects
                call_fast_args.append(convertedname)
        # return value conversion
        ct = self.ctret
        if ct == self.genc.pyobjtype:
            putresultin = 'oret'
            footer = None
        else:
            convert_to_obj = ct.opname_conv_to_obj  # simple conv only for now!
            print >> f, '\t%s;' % (ct.ctypetemplate % ('aret',))
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
            line = self.ctypeof(a).cincref(self.expr(a))
            if line:
                print >> f, '\t' + line

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
                    ct1 = self.ctypeof(a1)
                    ct2 = self.ctypeof(a2)
                    assert ct1 == ct2
                    line2 = ct1.cincref(self.expr(a2))
                    if line2:
                        line += '\t' + line2
                yield line
            for v in has_ref:
                line = self.ctypeof(v).cdecref(linklocalvars[v])
                if line:
                    yield line
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
                err   = 'err%d_%d' % (blocknum[block], len(to_release))
                macro = 'OP_%s' % op.opname.upper()
                meth  = getattr(self, macro, None)
                if meth:
                    yield meth(op, err)
                else:
                    lst = [self.expr(v) for v in op.args]
                    lst.append(self.expr(op.result))
                    lst.append(err)
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
                        self.genc.nameofvalue(link.exitcase),)
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
                ct = self.ctypeof(block.exitswitch)
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
                    line = self.ctypeof(v).cdecref(self.expr(v))
                    if line:
                        yield line
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield self.return_error

    # ____________________________________________________________

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWLIST0(%s, %s)' % (r, err)
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWDICT(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWDICT0(%s, %s)' % (r, err)
        else:
            assert len(args) % 2 == 0
            args.insert(0, '%d' % (len(args)//2))
            return 'OP_NEWDICT((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_NEWTUPLE(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_SIMPLE_CALL(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_CALL_ARGS(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        return 'OP_CALL_ARGS((%s), %s, %s)' % (', '.join(args), r, err)

    def OP_DIRECT_CALL(self, op, err):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        return '%s = %s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
            r, args[0], ', '.join(args[1:]), err)

    def OP_INCREF(self, op, err):
        v = op.args[0]
        return self.ctypeof(v).cincref(self.expr(v))

    def OP_DECREF(self, op, err):
        v = op.args[0]
        return self.ctypeof(v).cdecref(self.expr(v))

    def OP_CONV_TO_OBJ(self, op, err):
        v = op.args[0]
        convfnname = self.ctypeof(v).fn_conv_to_obj()
        return '%s = %s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
            self.expr(op.result), convfnname, self.expr(v), err)

    def OP_CONV_FROM_OBJ(self, op, err):
        v = op.args[0]
        convfnname = self.ctypeof(op.result).fn_conv_from_obj()
        return '%s = %s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
            self.expr(op.result), convfnname, self.expr(v), err)

# ____________________________________________________________

def dummy_wrapper(self, args, kwds):
    pass
