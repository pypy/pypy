from __future__ import generators
from pypy.translator.c.support import USESLOTS # set to False if necessary while refactoring
from pypy.translator.c.support import cdecl, ErrorValue
from pypy.translator.c.support import llvalue_from_constant, gen_assignments
from pypy.translator.c.support import c_string_constant
from pypy.objspace.flow.model import Variable, Constant, Block
from pypy.objspace.flow.model import c_last_exception, copygraph
from pypy.rpython.lltypesystem.lltype import Ptr, PyObject, Void, Bool, Signed
from pypy.rpython.lltypesystem.lltype import Unsigned, SignedLongLong, Float
from pypy.rpython.lltypesystem.lltype import UnsignedLongLong, Char, UniChar
from pypy.rpython.lltypesystem.lltype import pyobjectptr, ContainerType
from pypy.rpython.lltypesystem.lltype import Struct, Array, FixedSizeArray
from pypy.rpython.lltypesystem.lltype import ForwardReference, FuncType
from pypy.rpython.lltypesystem.llmemory import Address, WeakGcAddress
from pypy.translator.backendopt.ssa import SSI_to_SSA

PyObjPtr = Ptr(PyObject)
LOCALVAR = 'l_%s'

KEEP_INLINED_GRAPHS = False

class FunctionCodeGenerator(object):
    """
    Collects information about a function which we have to generate
    from a flow graph.
    """

    if USESLOTS:
        __slots__ = """graph db gcpolicy
                       exception_policy
                       more_ll_values
                       vars
                       lltypes
                       functionname
                       currentblock
                       blocknum
                       oldgraph""".split()

    def __init__(self, graph, db, exception_policy=None, functionname=None):
        self.graph = graph
        self.db = db
        self.gcpolicy = db.gcpolicy
        self.exception_policy = exception_policy
        self.functionname = functionname
        # apply the stackless transformation
        if db.stacklesstransformer:
            db.stacklesstransformer.transform_graph(graph)
        # apply the exception transformation
        if self.db.exctransformer:
            self.db.exctransformer.create_exception_handling(self.graph)
        # apply the gc transformation
        if self.db.gctransformer:
            self.db.gctransformer.transform_graph(self.graph)
        #self.graph.show()
        self.collect_var_and_types()

        for v in self.vars:
            T = getattr(v, 'concretetype', PyObjPtr)
            # obscure: skip forward references and hope for the best
            # (needed for delayed function pointers)
            if isinstance(T, Ptr) and T.TO.__class__ == ForwardReference:
                continue
            db.gettype(T)  # force the type to be considered by the database
       
        self.lltypes = None

    def collect_var_and_types(self):
        #
        # collect all variables and constants used in the body,
        # and get their types now
        #
        # NOTE: cannot use dictionaries with Constants as keys, because
        #       Constants may hash and compare equal but have different lltypes
        mix = [self.graph.getreturnvar()]
        self.more_ll_values = []
        for block in self.graph.iterblocks():
            mix.extend(block.inputargs)
            for op in block.operations:
                mix.extend(op.args)
                mix.append(op.result)
            for link in block.exits:
                mix.extend(link.getextravars())
                mix.extend(link.args)
                if hasattr(link, 'llexitcase'):
                    self.more_ll_values.append(link.llexitcase)
                elif link.exitcase is not None:
                    mix.append(Constant(link.exitcase))
        if self.exception_policy == "CPython":
            v, exc_cleanup_ops = self.graph.exc_cleanup
            mix.append(v)
            for cleanupop in exc_cleanup_ops:
                mix.extend(cleanupop.args)
                mix.append(cleanupop.result)
             
        uniquemix = []
        seen = {}
        for v in mix:
            if id(v) not in seen:
                uniquemix.append(v)
                seen[id(v)] = True
        self.vars = uniquemix

    def name(self, cname):  #virtual
        return cname

    def patch_graph(self, copy_graph):
        graph = self.graph
        if self.db.gctransformer and self.db.gctransformer.inline:
            if copy_graph:
                graph = copygraph(graph, shallow=True)
            self.db.gctransformer.inline_helpers(graph)
        return graph

    def implementation_begin(self):
        self.oldgraph = self.graph
        self.graph = self.patch_graph(copy_graph=True)
        SSI_to_SSA(self.graph)
        self.collect_var_and_types()
        self.blocknum = {}
        for block in self.graph.iterblocks():
            self.blocknum[block] = len(self.blocknum)
        db = self.db
        lltypes = {}
        for v in self.vars:
            T = getattr(v, 'concretetype', PyObjPtr)
            typename = db.gettype(T)
            lltypes[id(v)] = T, typename
        self.lltypes = lltypes

    def implementation_end(self):
        self.lltypes = None
        self.vars = None
        self.blocknum = None
        self.currentblock = None
        self.graph = self.oldgraph
        del self.oldgraph

    def argnames(self):
        return [LOCALVAR % v.name for v in self.graph.getargs()]

    def allvariables(self):
        return [v for v in self.vars if isinstance(v, Variable)]

    def allconstants(self):
        return [c for c in self.vars if isinstance(c, Constant)]

    def allconstantvalues(self):
        for c in self.vars:
            if isinstance(c, Constant):
                yield llvalue_from_constant(c)
        for llvalue in self.more_ll_values:
            yield llvalue

    def lltypemap(self, v):
        T, typename = self.lltypes[id(v)]
        return T

    def lltypename(self, v):
        T, typename = self.lltypes[id(v)]
        return typename

    def expr(self, v, special_case_void=True):
        if isinstance(v, Variable):
            if self.lltypemap(v) is Void and special_case_void:
                return '/* nothing */'
            else:
                return LOCALVAR % v.name
        elif isinstance(v, Constant):
            value = llvalue_from_constant(v)
            if value is None and not special_case_void:
                return 'nothing'
            else:
                return self.db.get(value)
        else:
            raise TypeError, "expr(%r)" % (v,)

    def error_return_value(self):
        returnlltype = self.lltypemap(self.graph.getreturnvar())
        return self.db.get(ErrorValue(returnlltype))

    def return_with_error(self):
        if self.exception_policy == "CPython":
            assert self.lltypemap(self.graph.getreturnvar()) == PyObjPtr
            v, exc_cleanup_ops = self.graph.exc_cleanup
            vanishing_exc_value = self.expr(v)
            yield 'RPyConvertExceptionToCPython(%s);' % vanishing_exc_value
            for cleanupop in exc_cleanup_ops:
                for line in self.gen_op(cleanupop):
                    yield line
        yield 'return %s; ' % self.error_return_value()

    # ____________________________________________________________

    def cfunction_declarations(self):
        # declare the local variables, excluding the function arguments
        seen = {}
        for a in self.graph.getargs():
            seen[a.name] = True

        result_by_name = []
        for v in self.allvariables():
            name = v.name
            if name not in seen:
                seen[name] = True
                result = cdecl(self.lltypename(v), LOCALVAR % name) + ';'
                if self.lltypemap(v) is Void:
                    continue  #result = '/*%s*/' % result
                result_by_name.append((v._name, result))
        result_by_name.sort()
        return [result for name, result in result_by_name]

    # ____________________________________________________________

    def cfunction_body(self):
        graph = self.graph

        # generate the body of each block
        for block in graph.iterblocks():
            self.currentblock = block
            myblocknum = self.blocknum[block]
            yield ''
            yield 'block%d:' % myblocknum
            for i, op in enumerate(block.operations):
                for line in self.gen_op(op):
                    yield line
            if len(block.exits) == 0:
                assert len(block.inputargs) == 1
                # regular return block
                if self.exception_policy == "CPython":
                    assert self.lltypemap(self.graph.getreturnvar()) == PyObjPtr
                    yield 'if (RPyExceptionOccurred()) {'
                    yield '\tRPyConvertExceptionToCPython();'
                    yield '\treturn NULL;'
                    yield '}'
                retval = self.expr(block.inputargs[0])
                if self.exception_policy != "exc_helper":
                    yield 'RPY_DEBUG_RETURN();'
                yield 'return %s;' % retval
                continue
            elif block.exitswitch is None:
                # single-exit block
                assert len(block.exits) == 1
                for op in self.gen_link(block.exits[0]):
                    yield op
            else:
                assert block.exitswitch != c_last_exception
                # block ending in a switch on a value
                TYPE = self.lltypemap(block.exitswitch)
                if TYPE in (Bool, PyObjPtr):
                    expr = self.expr(block.exitswitch)
                    for link in block.exits[:0:-1]:
                        assert link.exitcase in (False, True)
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
                        yield 'if (%s) {' % expr
                        for op in self.gen_link(link):
                            yield '\t' + op
                        yield '}'
                    link = block.exits[0]
                    assert link.exitcase in (False, True)
                    #yield 'assert(%s == %s);' % (self.expr(block.exitswitch),
                    #                       self.genc.nameofvalue(link.exitcase, ct))
                    for op in self.gen_link(link):
                        yield op
                elif TYPE in (Signed, Unsigned, SignedLongLong,
                              UnsignedLongLong, Char, UniChar):
                    defaultlink = None
                    expr = self.expr(block.exitswitch)
                    yield 'switch (%s) {' % self.expr(block.exitswitch)
                    for link in block.exits:
                        if link.exitcase == 'default':
                            defaultlink = link
                            continue
                        yield 'case %s:' % self.db.get(link.llexitcase)
                        for op in self.gen_link(link):
                            yield '\t' + op
                        yield 'break;'
                        
                    # Emit default case
                    yield 'default:'
                    if defaultlink is None:
                        yield '\tassert(!"bad switch!!");'
                    else:
                        for op in self.gen_link(defaultlink):
                            yield '\t' + op

                    yield '}'
                else:
                    raise TypeError("exitswitch type not supported"
                                    "  Got %r" % (TYPE,))

    def gen_link(self, link, linklocalvars=None):
        "Generate the code to jump across the given Link."
        is_alive = {}
        linklocalvars = linklocalvars or {}
        assignments = []
        for a1, a2 in zip(link.args, link.target.inputargs):
            a2type, a2typename = self.lltypes[id(a2)]
            if a2type is Void:
                continue
            if a1 in linklocalvars:
                src = linklocalvars[a1]
            else:
                src = self.expr(a1)
            dest = LOCALVAR % a2.name
            assignments.append((a2typename, dest, src))
        for line in gen_assignments(assignments):
            yield line
        yield 'goto block%d;' % self.blocknum[link.target]

    def gen_op(self, op):
        macro = 'OP_%s' % op.opname.upper()
        if op.opname.startswith('gc_'):
            meth = getattr(self.gcpolicy, macro, None)
            if meth:
                line = meth(self, op)
        else:
            meth = getattr(self, macro, None)
            if meth:
                line = meth(op)
        if meth is None:
            lst = [self.expr(v) for v in op.args]
            lst.append(self.expr(op.result))
            line = '%s(%s);' % (macro, ', '.join(lst))
        if "\n" not in line:
            yield line
        else:
            for line in line.splitlines():
                yield line

    # ____________________________________________________________

    # the C preprocessor cannot handle operations taking a variable number
    # of arguments, so here are Python methods that do it
    
    def OP_NEWLIST(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWLIST0(%s);' % (r, )
        else:
            args.insert(0, '%d' % len(args))
            return 'OP_NEWLIST((%s), %s);' % (', '.join(args), r)

    def OP_NEWDICT(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        if len(args) == 0:
            return 'OP_NEWDICT0(%s);' % (r, )
        else:
            assert len(args) % 2 == 0
            args.insert(0, '%d' % (len(args)//2))
            return 'OP_NEWDICT((%s), %s);' % (', '.join(args), r)

    def OP_NEWTUPLE(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.insert(0, '%d' % len(args))
        return 'OP_NEWTUPLE((%s), %s);' % (', '.join(args), r)

    def OP_SIMPLE_CALL(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        args.append('NULL')
        return 'OP_SIMPLE_CALL((%s), %s);' % (', '.join(args), r)

    def OP_CALL_ARGS(self, op):
        args = [self.expr(v) for v in op.args]
        r = self.expr(op.result)
        return 'OP_CALL_ARGS((%s), %s);' % (', '.join(args), r)

    def generic_call(self, FUNC, fnexpr, args_v, v_result):
        args = []
        assert len(args_v) == len(FUNC.TO.ARGS)
        for v, ARGTYPE in zip(args_v, FUNC.TO.ARGS):
            if ARGTYPE is Void:
                continue    # skip 'void' argument
            args.append(self.expr(v))
            # special case for rctypes: by-value container args:
            if isinstance(ARGTYPE, ContainerType):
                args[-1] = '*%s' % (args[-1],)

        line = '%s(%s);' % (fnexpr, ', '.join(args))
        if self.lltypemap(v_result) is not Void:
            # skip assignment of 'void' return value
            r = self.expr(v_result)
            line = '%s = %s' % (r, line)
        return line

    def OP_DIRECT_CALL(self, op):
        fn = op.args[0]
        return self.generic_call(fn.concretetype, self.expr(fn),
                                 op.args[1:], op.result)

    def OP_INDIRECT_CALL(self, op):
        fn = op.args[0]
        return self.generic_call(fn.concretetype, self.expr(fn),
                                 op.args[1:-1], op.result)

    def OP_ADR_CALL(self, op):
        ARGTYPES = [v.concretetype for v in op.args[1:]]
        RESTYPE = op.result.concretetype
        FUNC = Ptr(FuncType(ARGTYPES, RESTYPE))
        typename = self.db.gettype(FUNC)
        fnaddr = op.args[0]
        fnexpr = '((%s)%s)' % (cdecl(typename, ''), self.expr(fnaddr))
        return self.generic_call(FUNC, fnexpr, op.args[1:], op.result)

    # low-level operations
    def generic_get(self, op, sourceexpr):
        T = self.lltypemap(op.result)
        newvalue = self.expr(op.result, special_case_void=False)
        result = ['%s = %s;' % (newvalue, sourceexpr)]
        result = '\n'.join(result)
        if T is Void:
            result = '/* %s */' % result
        return result

    def generic_set(self, op, targetexpr):
        newvalue = self.expr(op.args[2], special_case_void=False)
        result = ['%s = %s;' % (targetexpr, newvalue)]
        T = self.lltypemap(op.args[2])
        result = '\n'.join(result)
        if T is Void:
            result = '/* %s */' % result
        return result

    def OP_GETFIELD(self, op, ampersand=''):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        expr = ampersand + structdef.ptr_access_expr(self.expr(op.args[0]),
                                                     op.args[1].value)
        return self.generic_get(op, expr)

    def OP_SETFIELD(self, op):
        assert isinstance(op.args[1], Constant)
        STRUCT = self.lltypemap(op.args[0]).TO
        structdef = self.db.gettypedefnode(STRUCT)
        expr = structdef.ptr_access_expr(self.expr(op.args[0]),
                                         op.args[1].value)
        return self.generic_set(op, expr)

    OP_BARE_SETFIELD = OP_SETFIELD

    def OP_GETSUBSTRUCT(self, op):
        RESULT = self.lltypemap(op.result).TO
        if isinstance(RESULT, FixedSizeArray):
            return self.OP_GETFIELD(op, ampersand='')
        else:
            return self.OP_GETFIELD(op, ampersand='&')

    def OP_GETARRAYSIZE(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        if isinstance(ARRAY, FixedSizeArray):
            return '%s = %d;' % (self.expr(op.result),
                                 ARRAY.length)
        else:
            return '%s = %s->length;' % (self.expr(op.result),
                                         self.expr(op.args[0]))

    def OP_GETARRAYITEM(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if not isinstance(ARRAY, FixedSizeArray):
            items += '->items'
        return self.generic_get(op, '%s[%s]' % (items,
                                                self.expr(op.args[1])))

    def OP_SETARRAYITEM(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if not isinstance(ARRAY, FixedSizeArray):
            items += '->items'
        return self.generic_set(op, '%s[%s]' % (items,
                                                self.expr(op.args[1])))
    OP_BARE_SETARRAYITEM = OP_SETARRAYITEM

    def OP_GETARRAYSUBSTRUCT(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if not isinstance(ARRAY, FixedSizeArray):
            items += '->items'
        return '%s = %s + %s;' % (self.expr(op.result),
                                  items,
                                  self.expr(op.args[1]))

    def OP_PTR_NONZERO(self, op):
        return '%s = (%s != NULL);' % (self.expr(op.result),
                                       self.expr(op.args[0]))
    def OP_PTR_ISZERO(self, op):
        return '%s = (%s == NULL);' % (self.expr(op.result),
                                       self.expr(op.args[0]))
    
    def OP_PTR_EQ(self, op):
        return '%s = (%s == %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_PTR_NE(self, op):
        return '%s = (%s != %s);' % (self.expr(op.result),
                                     self.expr(op.args[0]),
                                     self.expr(op.args[1]))

    def OP_BOEHM_MALLOC(self, op):
        return 'OP_BOEHM_ZERO_MALLOC(%s, %s, void*, 0, 0);' % (self.expr(op.args[0]),
                                                               self.expr(op.result))

    def OP_BOEHM_MALLOC_ATOMIC(self, op):
        return 'OP_BOEHM_ZERO_MALLOC(%s, %s, void*, 1, 0);' % (self.expr(op.args[0]),
                                                               self.expr(op.result))

    def OP_BOEHM_REGISTER_FINALIZER(self, op):
        return 'GC_REGISTER_FINALIZER(%s, (GC_finalization_proc)%s, NULL, NULL, NULL);' \
               % (self.expr(op.args[0]), self.expr(op.args[1]))

    def OP_RAW_MALLOC(self, op):
        eresult = self.expr(op.result)
        esize = self.expr(op.args[0])
        return "OP_RAW_MALLOC(%s, %s, void *);" % (esize, eresult)

    def OP_FLAVORED_MALLOC(self, op):
        # XXX this function should DIE!
        TYPE = self.lltypemap(op.result).TO
        typename = self.db.gettype(TYPE)
        eresult = self.expr(op.result)
        esize = 'sizeof(%s)' % cdecl(typename, '')
        erestype = cdecl(typename, '*')
        flavor = op.args[0].value
        if flavor == "raw": 
            return "OP_RAW_MALLOC(%s, %s, %s);" % (esize, eresult, erestype)
        elif flavor == "stack": 
            return "OP_STACK_MALLOC(%s, %s, %s);" % (esize, eresult, erestype)
        elif flavor == "cpy":
            cpytype = self.expr(op.args[2])
            return "OP_CPY_MALLOC(%s, %s, %s);" % (cpytype, eresult, erestype)
        else:
            raise NotImplementedError

    def OP_FLAVORED_MALLOC_VARSIZE(self, op):
        # XXX this function should DIE!, at least twice over
        # XXX I know this working in just one case, probably makes
        # sense to assert it here, rest is just copied
        flavor = op.args[0].value
        assert flavor == 'raw'
        TYPE = self.lltypemap(op.result).TO
        assert isinstance(TYPE, Array)
        assert TYPE._hints.get('nolength', False)
        # </obscure hack>
        typename = self.db.gettype(TYPE)
        lenfld = 'length'
        nodedef = self.db.gettypedefnode(TYPE)
        if isinstance(TYPE, Struct):
            arfld = TYPE._arrayfld
            lenfld = "%s.length" % nodedef.c_struct_field_name(arfld)
            VARPART = TYPE._flds[TYPE._arrayfld]
        else:
            VARPART = TYPE
        assert isinstance(VARPART, Array)
        itemtypename = self.db.gettype(VARPART.OF)
        elength = self.expr(op.args[2])
        eresult = self.expr(op.result)
        erestype = cdecl(typename, '*')
        if VARPART.OF is Void:    # strange
            esize = 'sizeof(%s)' % (cdecl(typename, ''),)
            result = '{\n'
        else:
            itemtype = cdecl(itemtypename, '')
            result = 'IF_VARSIZE_OVERFLOW(%s, %s, %s)\nelse {\n' % (
                elength,
                itemtype,
                eresult)
            esize = 'sizeof(%s)-sizeof(%s)+%s*sizeof(%s)' % (
                cdecl(typename, ''),
                itemtype,
                elength,
                itemtype)

        # ctypes Arrays have no length field
        if not VARPART._hints.get('nolength', False):
            result += '\nif(%s) %s->%s = %s;' % (eresult, eresult, lenfld, elength)
        if flavor == "raw": 
            result += "OP_RAW_MALLOC(%s, %s, %s);" % (esize, eresult, erestype)
        elif flavor == "stack": 
            result += "OP_STACK_MALLOC(%s, %s, %s);" % (esize, eresult, erestype)
        elif flavor == "cpy":
            xxx # this will never work, as I don't know which arg it would be
            # tests, tests, tests....
            cpytype = self.expr(op.args[2])
            result += "OP_CPY_MALLOC(%s, %s, %s);" % (cpytype, eresult, erestype)
        else:
            raise NotImplementedError
        
        result += '\n}'
        return result

    def OP_FLAVORED_FREE(self, op):
        flavor = op.args[0].value
        if flavor == "raw":
            return "OP_RAW_FREE(%s, %s)" % (self.expr(op.args[1]),
                                            self.expr(op.result))
        elif flavor == "cpy":
            return "OP_CPY_FREE(%s)" % (self.expr(op.args[1]),)
        else:
            raise NotImplementedError

    def OP_DIRECT_FIELDPTR(self, op):
        return self.OP_GETFIELD(op, ampersand='&')

    def OP_DIRECT_ARRAYITEMS(self, op):
        ARRAY = self.lltypemap(op.args[0]).TO
        items = self.expr(op.args[0])
        if not isinstance(ARRAY, FixedSizeArray):
            items += '->items'
        return '%s = %s;' % (self.expr(op.result), items)

    def OP_DIRECT_PTRADD(self, op):
        return '%s = %s + %s;' % (self.expr(op.result),
                                  self.expr(op.args[0]),
                                  self.expr(op.args[1]))

    def OP_CAST_POINTER(self, op):
        TYPE = self.lltypemap(op.result)
        typename = self.db.gettype(TYPE)
        result = []
        result.append('%s = (%s)%s;' % (self.expr(op.result),
                                        cdecl(typename, ''),
                                        self.expr(op.args[0])))
        return '\t'.join(result)

    OP_CAST_PTR_TO_ADR = OP_CAST_POINTER
    OP_CAST_ADR_TO_PTR = OP_CAST_POINTER
    OP_CAST_OPAQUE_PTR = OP_CAST_POINTER

    def OP_CAST_PTR_TO_WEAKADR(self, op):
        return '%s = HIDE_POINTER(%s);' % (self.expr(op.result),
                                             self.expr(op.args[0]))

    def OP_CAST_WEAKADR_TO_PTR(self, op):
        TYPE = self.lltypemap(op.result)
        assert TYPE != PyObjPtr
        typename = self.db.gettype(TYPE)
        return '%s = (%s)REVEAL_POINTER(%s);' % (self.expr(op.result),
                                                   cdecl(typename, ''),
                                                   self.expr(op.args[0]))

    def OP_CAST_INT_TO_PTR(self, op):
        TYPE = self.lltypemap(op.result)
        typename = self.db.gettype(TYPE)
        return "%s = (%s)%s;" % (self.expr(op.result), cdecl(typename, ""), 
                                 self.expr(op.args[0]))

    def OP_SAME_AS(self, op):
        result = []
        TYPE = self.lltypemap(op.result)
        assert self.lltypemap(op.args[0]) == TYPE
        if TYPE is not Void:
            result.append('%s = %s;' % (self.expr(op.result),
                                        self.expr(op.args[0])))
        return '\t'.join(result)

    def OP_HINT(self, op):
        hints = op.args[1].value
        return '%s\t/* hint: %r */' % (self.OP_SAME_AS(op), hints)

    def OP_KEEPALIVE(self, op): # xxx what should be the sematics consequences of this
        return "/* kept alive: %s */ ;" % self.expr(op.args[0], special_case_void=False)

    #address operations
    def OP_RAW_STORE(self, op):
        addr = self.expr(op.args[0])
        TYPE = op.args[1].value
        offset = self.expr(op.args[2])
        value = self.expr(op.args[3])
        typename = cdecl(self.db.gettype(TYPE).replace('@', '*@'), '')
        return "*(((%(typename)s) %(addr)s ) + %(offset)s) = %(value)s;" % locals()

    def OP_RAW_LOAD(self, op):
        addr = self.expr(op.args[0])
        TYPE = op.args[1].value
        offset = self.expr(op.args[2])
        result = self.expr(op.result)
        typename = cdecl(self.db.gettype(TYPE).replace('@', '*@'), '')
        return "%(result)s = *(((%(typename)s) %(addr)s ) + %(offset)s);" % locals()

    def OP_CAST_PRIMITIVE(self, op):
        TYPE = self.lltypemap(op.result)
        val =  self.expr(op.args[0])
        ORIG = self.lltypemap(op.args[0])
        if ORIG is Char:
            val = "(unsigned char)%s" % val
        elif ORIG is UniChar:
            val = "(unsigned long)%s" % val
        result = self.expr(op.result)
        typename = cdecl(self.db.gettype(TYPE), '')        
        return "%(result)s = (%(typename)s)(%(val)s);" % locals()

    def OP_RESUME_POINT(self, op):
        return '/* resume point %s */'%(op.args[0],)

    def OP_DEBUG_PRINT(self, op):
        # XXX
        from pypy.rpython.lltypesystem.rstr import STR
        format = []
        argv = []
        for arg in op.args:
            T = arg.concretetype
            if T == Ptr(STR):
                if isinstance(arg, Constant):
                    format.append(''.join(arg.value.chars).replace('%', '%%'))
                else:
                    format.append('%s')
                    argv.append('RPyString_AsString(%s)' % self.expr(arg))
                continue
            elif T == Signed:
                format.append('%d')
            elif T == Float:
                format.append('%f')
            elif isinstance(T, Ptr) or T in (Address, WeakGcAddress):
                format.append('%p')
            elif T == Char:
                if isinstance(arg, Constant):
                    format.append(arg.value.replace('%', '%%'))
                    continue
                format.append('%c')
            else:
                raise Exception("don't know how to debug_print %r" % (T,))
            argv.append(self.expr(arg))
        return "fprintf(stderr, %s%s);" % (
            c_string_constant(' '.join(format) + '\n\000'),
            ''.join([', ' + s for s in argv]))

    def OP_DEBUG_ASSERT(self, op):
        return 'RPyAssert(%s, %s);' % (self.expr(op.args[0]),
                                       c_string_constant(op.args[1].value))

    def OP_DEBUG_FATALERROR(self, op):
        # XXX
        from pypy.rpython.lltypesystem.rstr import STR
        msg = op.args[0]
        assert msg.concretetype == Ptr(STR)
        argv = []
        if isinstance(msg, Constant):
            msg = c_string_constant(''.join(msg.value.chars))
        else:
            msg = 'RPyString_AsString(%s)' % self.expr(msg)

        return 'fprintf(stderr, "%%s\\n", %s); abort();' % msg

    def OP_INSTRUMENT_COUNT(self, op):
        counter_label = op.args[1].value
        self.db.instrument_ncounter = max(self.db.instrument_ncounter,
                                          counter_label+1)
        counter_label = self.expr(op.args[1])
        return 'INSTRUMENT_COUNT(%s);' % counter_label
            
    def OP_IS_EARLY_CONSTANT(self, op):
        return self.expr(op.result)  + ' = 0;' # Allways false
    
assert not USESLOTS or '__dict__' not in dir(FunctionCodeGenerator)
