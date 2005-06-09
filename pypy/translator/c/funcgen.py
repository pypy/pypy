from __future__ import generators
from pypy.translator.c.support import cdecl, ErrorValue
from pypy.translator.c.support import llvalue_from_constant
from pypy.objspace.flow.model import Variable, Constant, Block
from pypy.objspace.flow.model import traverse, uniqueitems, last_exception
from pypy.rpython.lltype import Ptr, PyObject, Void, Bool
from pypy.rpython.lltype import pyobjectptr, Struct, Array
from pypy.translator.unsimplify import remove_direct_loops


PyObjPtr = Ptr(PyObject)

class FunctionCodeGenerator:
    """
    Collects information about a function which we have to generate
    from a flow graph.
    """

    def __init__(self, graph, db):
        self.graph = graph
        remove_direct_loops(None, graph)
        self.db = db
        self.lltypemap = self.collecttypes()
        self.typemap = {}
        for v, T in self.lltypemap.items():
            self.typemap[v] = db.gettype(T)

    def collecttypes(self):
        # collect all variables and constants used in the body,
        # and get their types now
        result = []
        def visit(block):
            if isinstance(block, Block):
                result.extend(block.inputargs)
                for op in block.operations:
                    result.extend(op.args)
                    result.append(op.result)
                for link in block.exits:
                    result.extend(link.getextravars())
                    result.extend(link.args)
                    result.append(Constant(link.exitcase))
        traverse(visit, self.graph)
        resultvar = self.graph.getreturnvar()
        lltypemap = {resultvar: Void}   # default value, normally overridden
        for v in uniqueitems(result):
            # xxx what kind of pointer for constants?
            T = getattr(v, 'concretetype', PyObjPtr)           
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

    def expr(self, v):
        if isinstance(v, Variable):
            if self.lltypemap[v] == Void:
                return '/* nothing */'
            else:
                return v.name
        elif isinstance(v, Constant):
            return self.db.get(llvalue_from_constant(v))
        else:
            raise TypeError, "expr(%r)" % (v,)

    def error_return_value(self):
        returnlltype = self.lltypemap[self.graph.getreturnvar()]
        return self.db.get(ErrorValue(returnlltype))

    # ____________________________________________________________

    def cfunction_declarations(self):
        # declare the local variables, excluding the function arguments
        inputargset = {}
        for a in self.graph.getargs():
            inputargset[a] = True

        result_by_name = []
        for v in self.allvariables():
            if v not in inputargset:
                result = cdecl(self.typemap[v], v.name) + ';'
                if self.lltypemap[v] == Void:
                    result = '/*%s*/' % result
                result_by_name.append((v._name, result))
        result_by_name.sort()
        return [result for name, result in result_by_name]

    # ____________________________________________________________

    def cfunction_body(self):
        graph = self.graph

        blocknum = {}
        allblocks = []

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
                if self.lltypemap[a2] == Void:
                    continue
                if a1 in linklocalvars:
                    src = linklocalvars[a1]
                else:
                    src = self.expr(a1)
                line = '%s = %s;' % (self.expr(a2), src)
                if a1 in has_ref:
                    del has_ref[a1]
                else:
                    assert self.lltypemap[a1] == self.lltypemap[a2]
                    line += '\t' + self.cincref(a2)
                yield line
            for v in has_ref:
                line = self.cdecref(v, linklocalvars[v])
                if line:
                    yield line
            yield 'goto block%d;' % blocknum[link.target]

        # collect all blocks
        def visit(block):
            if isinstance(block, Block):
                allblocks.append(block)
                blocknum[block] = len(blocknum)
        traverse(visit, graph)

        assert graph.startblock is allblocks[0]

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
                        self.db.get(pyobjectptr(link.exitcase)),)
                    yield '\tPyObject *exc_cls, *exc_value, *exc_tb;'
                    yield '\tPyErr_Fetch(&exc_cls, &exc_value, &exc_tb);'
                    yield '\tif (exc_value == NULL) {'
                    yield '\t\texc_value = Py_None;'
                    yield '\t\tPy_INCREF(Py_None);'
                    yield '\t}'
                    yield '\tPy_XDECREF(exc_tb);'
                    d = {}
                    if isinstance(link.last_exception, Variable):
                        d[link.last_exception] = 'exc_cls'
                    else:
                        yield '\tPy_XDECREF(exc_cls);'
                    if isinstance(link.last_exc_value, Variable):
                        d[link.last_exc_value] = 'exc_value'
                    else:
                        yield '\tPy_XDECREF(exc_value);'
                    for op in gen_link(link, d):
                        yield '\t' + op
                    yield '}'
                err_reachable = True
            else:
                # block ending in a switch on a value
                TYPE = self.lltypemap[block.exitswitch]
                for link in block.exits[:-1]:
                    assert link.exitcase in (False, True)
                    expr = self.expr(block.exitswitch)
                    if TYPE == Bool:
                        if not link.exitcase:
                            expr = '!' + expr
                    elif TYPE == PyObjPtr:
                        yield 'assert(%s == Py_True || %s == Py_False);' % (
                            expr, expr)
                        if link.exitcase:
                            expr = '%s == Py_True' % expr
                        else:
                            expr = '%s == Py_False' % expr
                    else:
                        raise TypeError("switches can only be on Bool or "
                                        "PyObjPtr.  Got %r" % (TYPE,))
                    yield 'if (%s) {' % expr
                    for op in gen_link(link):
                        yield '\t' + op
                    yield '}'
                link = block.exits[-1]
                assert link.exitcase in (False, True)
                #yield 'assert(%s == %s);' % (self.expr(block.exitswitch),
                #                       self.genc.nameofvalue(link.exitcase, ct))
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
        # skip 'void' arguments
        args = [self.expr(v) for v in op.args if self.lltypemap[v] != Void]
        if self.lltypemap[op.result] == Void:
            # skip assignment of 'void' return value
            return '%s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
                args[0], ', '.join(args[1:]), err)
        else:
            r = self.expr(op.result)
            return '%s = %s(%s); if (PyErr_Occurred()) FAIL(%s)' % (
                r, args[0], ', '.join(args[1:]), err)

    # low-level operations
    def generic_get(self, op, sourceexpr):
        newvalue = self.expr(op.result)
        result = ['%s = %s;' % (newvalue, sourceexpr)]
        # need to adjust the refcount of the result
        T = self.lltypemap[op.result]
        increfstmt = self.db.cincrefstmt(newvalue, T)
        if increfstmt:
            result.append(increfstmt)
        result = '\t'.join(result)
        if T == Void:
            result = '/* %s */' % result
        return result

    def generic_set(self, op, targetexpr):
        newvalue = self.expr(op.args[2])
        result = ['%s = %s;' % (targetexpr, newvalue)]
        # need to adjust some refcounts
        T = self.lltypemap[op.args[2]]
        decrefstmt = self.db.cdecrefstmt('prev', T)
        increfstmt = self.db.cincrefstmt(newvalue, T)
        if increfstmt:
            result.append(increfstmt)
        if decrefstmt:
            result.insert(0, '{ %s = %s;' % (
                cdecl(self.typemap[op.args[2]], 'prev'),
                targetexpr))
            result.append(decrefstmt)
            result.append('}')
        result = '\t'.join(result)
        if T == Void:
            result = '/* %s */' % result
        return result

    def OP_GETFIELD(self, op, err, ampersand=''):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap[op.args[0]].TO
        structdef = self.db.gettypedefnode(STRUCT)
        fieldname = structdef.c_struct_field_name(op.args[1].value)
        return self.generic_get(op, '%s%s->%s' % (ampersand,
                                                  self.expr(op.args[0]),
                                                  fieldname))

    def OP_SETFIELD(self, op, err):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap[op.args[0]].TO
        structdef = self.db.gettypedefnode(STRUCT)
        fieldname = structdef.c_struct_field_name(op.args[1].value)
        return self.generic_set(op, '%s->%s' % (self.expr(op.args[0]),
                                                fieldname))

    def OP_GETSUBSTRUCT(self, op, err):
        return self.OP_GETFIELD(op, err, ampersand='&')

    def OP_GETARRAYSIZE(self, op, err):
        return '%s = %s->length;' % (self.expr(op.result),
                                     self.expr(op.args[0]))

    def OP_GETARRAYITEM(self, op, err):
        return self.generic_get(op, '%s->items[%s]' % (self.expr(op.args[0]),
                                                       self.expr(op.args[1])))

    def OP_SETARRAYITEM(self, op, err):
        return self.generic_set(op, '%s->items[%s]' % (self.expr(op.args[0]),
                                                       self.expr(op.args[1])))

    def OP_GETARRAYSUBSTRUCT(self, op, err):
        return '%s = %s->items + %s;' % (self.expr(op.result),
                                         self.expr(op.args[0]),
                                         self.expr(op.args[1]))

    def OP_PTR_NONZERO(self, op, err):
        return '%s = (%s != NULL);' % (self.expr(op.result),
                                       self.expr(op.args[0]))

    def OP_PTR_EQ(self, op, err):
        return '%s = (%s == %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_PTR_NE(self, op, err):
        return '%s = (%s != %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_MALLOC(self, op, err):
        TYPE = self.lltypemap[op.result].TO
        typename = self.db.gettype(TYPE)
        eresult = self.expr(op.result)
        result = ['OP_ZERO_MALLOC(sizeof(%s), %s, %s)' % (cdecl(typename, ''),
                                                          eresult,
                                                          err),
                  '%s->%s = 1;' % (eresult,
                                   self.db.gettypedefnode(TYPE).refcount),
                  ]
        return '\t'.join(result)

    def OP_MALLOC_VARSIZE(self, op, err):
        TYPE = self.lltypemap[op.result].TO
        typename = self.db.gettype(TYPE)
        lenfld = 'length'
        nodedef = self.db.gettypedefnode(TYPE)
        if isinstance(TYPE, Struct):
            arfld = TYPE._arrayfld
            lenfld = "%s.length" % nodedef.c_struct_field_name(arfld)
            TYPE = TYPE._flds[TYPE._arrayfld]
        assert isinstance(TYPE, Array)
        itemtypename = self.db.gettype(TYPE.OF)
        elength = self.expr(op.args[1])
        eresult = self.expr(op.result)
        if TYPE.OF == Void:    # strange
            size = 'sizeof(%s)' % (cdecl(typename, ''),)
        else:
            size = 'sizeof(%s)+((%s-1)*sizeof(%s))' % (cdecl(typename, ''),
                                                       elength,
                                                       cdecl(itemtypename, ''))
        result = ['OP_ZERO_MALLOC(%s, %s, %s)' % (size,
                                                  eresult,
                                                  err),
                  '%s->%s = %s;' % (eresult, lenfld,
                                    elength),
                  '%s->%s = 1;' % (eresult,
                                   nodedef.refcount),
                  ]
        return '\t'.join(result)

    def OP_CAST_PARENT(self, op, err):
        TYPE = self.lltypemap[op.result]
        typename = self.db.gettype(TYPE)
        return '%s = (%s)%s;' % (self.expr(op.result),
                                 cdecl(typename, ''),
                                 self.expr(op.args[0]))

    def OP_SAME_AS(self, op, err):
        result = []
        assert self.lltypemap[op.args[0]] == self.lltypemap[op.result]
        if self.lltypemap[op.result] != Void:
            result.append('%s = %s;' % (self.expr(op.result),
                                        self.expr(op.args[0])))
            line = self.cincref(op.result)
            if line:
                result.append(line)
        return '\t'.join(result)

    def cincref(self, v):
        T = self.lltypemap[v]
        return self.db.cincrefstmt(v.name, T)

    def cdecref(self, v, expr=None):
        T = self.lltypemap[v]
        return self.db.cdecrefstmt(expr or v.name, T)
