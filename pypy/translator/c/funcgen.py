from __future__ import generators
from pypy.translator.gensupp import ordered_blocks
from pypy.translator.c.support import cdecl, ErrorValue
from pypy.translator.c.support import llvalue_from_constant
from pypy.objspace.flow.model import Variable, Constant, Block
from pypy.objspace.flow.model import traverse, uniqueitems
from pypy.rpython.lltype import GcPtr, NonGcPtr, PyObject, Void, Primitive


PyObjGcPtr    = GcPtr(PyObject)
PyObjNonGcPtr = NonGcPtr(PyObject)


class FunctionCodeGenerator:
    """
    Collects information about a function which we have to generate
    from a flow graph.
    """

    def __init__(self, graph, gettype, getvalue):
        self.graph = graph
        self.getvalue = getvalue
        self.lltypemap = self.collecttypes()
        self.typemap = {}
        for v, T in self.lltypemap.items():
            self.typemap[v] = gettype(T)

    def collecttypes(self):
        # collect all variables and constants used in the body,
        # and get their types now
        result = []
        def visit(block):
            if isinstance(block, Block):
                result.extend(block.inputargs)
                for op in block.operations:
                    result.extend(op.args)
                for link in block.exits:
                    result.extend(link.args)
        traverse(visit, self.graph)
        resultvar = self.graph.getreturnvar()
        lltypemap = {resultvar: Void}   # default value, normally overridden
        for v in uniqueitems(result):
            if isinstance(v, Variable):
                T = getattr(v, 'concretetype', PyObjGcPtr)
            else:
                T = getattr(v, 'concretetype', PyObjNonGcPtr)
            lltypemap[v] = T
        return lltypemap

    def argnames(self):
        return [v.name for v in self.graph.getargs()]

    def allvariables(self):
        return [v for v in self.typemap if isinstance(v, Variable)]

    def allconstants(self):
        return [v for v in self.typemap if isinstance(v, Constant)]

    def allconstantvalues(self):
        for v in self.typemap:
            if isinstance(v, Constant):
                yield llvalue_from_constant(v)

    def decl(self, v):
        assert isinstance(v, Variable), repr(v)
        return cdecl(self.typemap[v], v.name)

    def expr(self, v):
        if isinstance(v, Variable):
            return v.name
        elif isinstance(v, Constant):
            return self.getvalue(llvalue_from_constant(v))
        else:
            raise TypeError, "expr(%r)" % (v,)

    def error_return_value(self):
        returnlltype = self.lltypemap[self.graph.getreturnvar()]
        return self.getvalue(ErrorValue(returnlltype))

    # ____________________________________________________________

    def cfunction_declarations(self):
        # declare the local variables, excluding the function arguments
        inputargset = {}
        for a in self.graph.getargs():
            inputargset[a] = True

        for v in self.allvariables():
            if v not in inputargset:
                yield '%s;' % self.decl(v)

    # ____________________________________________________________

    def cfunction_body(self):
        graph = self.graph

        # generate an incref for each input argument
        for a in self.graph.getargs():
            line = self.cincref(a)
            if line:
                yield line

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
                line = '%s = %s;' % (self.expr(a2), src)
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    ct1 = self.ctypeof(a1)
                    ct2 = self.ctypeof(a2)
                    assert ct1 == ct2
                    line += '\t' + self.cincref(a2)
                yield line
            for v in has_ref:
                yield self.cdecref(v, linklocalvars[v])
            yield 'goto block%d;' % blocknum[link.target]

        # collect all blocks
        allblocks = ordered_blocks(graph)
        blocknum = {}
        for block in allblocks:
            blocknum[block] = len(blocknum)

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
                    yield 'return %s;' % self.error_return_value()
                else:
                    # regular return block
                    retval = self.expr(block.inputargs[0])
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
                                link.last_exception: 'exc_cls',
                                link.last_exc_value: 'exc_value'}):
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
                    yield self.cdecref(v)
                yield 'err%d_%d:' % (blocknum[block], len(to_release))
                err_reachable = True
            if err_reachable:
                yield 'return %s;' % self.error_return_value()

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

    def OP_INST_GETATTR(self, op, err):
        return '%s = INST_ATTR_%s__%s(%s);' % (
            self.expr(op.result),
            op.args[0].concretetype.typename,
            op.args[1].value,
            self.expr(op.args[0]))

    def OP_INST_SETATTR(self, op, err):
        return 'INST_ATTR_%s__%s(%s) = %s;' % (
            op.args[0].concretetype.typename,
            op.args[1].value,
            self.expr(op.args[0]),
            self.expr(op.args[2]))

    def OP_CONV_TO_OBJ(self, op, err):
        v = op.args[0]
        return '%s = CONV_TO_OBJ_%s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
            self.expr(op.result), self.ctypeof(v).typename, self.expr(v), err)

    def OP_CONV_FROM_OBJ(self, op, err):
        v = op.args[0]
        return '%s = CONV_FROM_OBJ_%s(%s); if (PyErr_Occurred()) FAIL(%s)' %(
            self.expr(op.result), self.ctypeof(op.result).typename,
            self.expr(v), err)

    def OP_INCREF(self, op, err):
        return self.cincref(op.args[0])

    def OP_DECREF(self, op, err):
        return self.cdecref(op.args[0])

    def cincref(self, v):
        T = self.lltypemap[v]
        if not isinstance(T, Primitive) and 'gc' in T.flags:
            if T.TO == PyObject:
                return 'Py_INCREF(%s);' % v.name
            else:
                return '/*XXX INCREF*/'
        else:
            return ''

    def cdecref(self, v, expr=None):
        T = self.lltypemap[v]
        if not isinstance(T, Primitive) and 'gc' in T.flags:
            if T.TO == PyObject:
                return 'Py_DECREF(%s);' % v.name
            else:
                return '/*XXX DECREF*/'
        else:
            return ''
