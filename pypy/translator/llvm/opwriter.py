from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype
from pypy.translator.llvm.log import log 

log = log.opwriter

class OpRepr(object):
    __slots__ = "db op retref rettype argrefs argtypes".split()
    def __init__(self, op, db):
        self.db = db
        self.op = op
        self.argrefs = db.repr_arg_multi(op.args)
        self.argtypes = db.repr_arg_type_multi(op.args)
        self.retref = db.repr_arg(op.result)
        self.rettype = db.repr_arg_type(op.result)

class OpReprCall(OpRepr):
    __slots__ = "db op retref rettype argrefs argtypes".split()
    def __init__(self, op, db):
        super(OpReprCall, self).__init__(op, db)
        self.argrefs = [aref for arg, aref in zip(op.args, self.argrefs)
                        if arg.concretetype is not lltype.Void]
        self.argtypes = [atype for arg, atype in zip(op.args, self.argtypes)
                         if arg.concretetype is not lltype.Void]
        if self.db.is_function_ptr(self.op.result):
            self.rettype  = "%s (%s)*" % (self.rettype,
                                          ", ".join(self.argtypes[1:]))

class OpWriter(object):            
  
    shift_operations = {
        'int_lshift': 'shl',
        'int_rshift': 'lshr',
        
        'uint_lshift': 'shl',
        'uint_rshift': 'lshr',
        
        'llong_lshift': 'shl',
        'llong_rshift': 'lshr',
        'ullong_lshift': 'shl',
        'ullong_rshift': 'lshr',
        }

    binary_operations = {
        'float_mul'     : 'mul',
        'float_add'     : 'add',
        'float_sub'     : 'sub',
        'float_truediv' : 'fdiv',
        'ptr_eq'        : 'icmp eq',
        'ptr_ne'        : 'icmp ne' }

    # generic numeric ops
    for tt in 'int llong ullong uint'.split():
        for oo in 'mul add sub and or xor'.split():
            binary_operations['%s_%s' % (tt, oo)] = oo

    for tt in 'llong int'.split():
        binary_operations['%s_floordiv' % tt] = 'sdiv'
        binary_operations['%s_mod' % tt] = 'srem'

    for tt in 'ullong uint'.split():
        binary_operations['%s_floordiv' % tt] = 'udiv'
        binary_operations['%s_mod' % tt] = 'urem'

    # comparison ops
    for tt in 'int llong unichar'.split():
        for oo in 'eq ne'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'icmp %s' % oo
        for oo in 'lt le ge gt'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'icmp s%s' % oo
            
    for tt in 'ullong uint'.split():
        for oo in 'eq ne'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'icmp %s' % oo
        for oo in 'lt le ge gt'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'icmp u%s' % oo

    for tt in 'float'.split():
        for oo in 'lt le eq ne ge gt'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'fcmp o%s' % oo

    binary_operations.update({'char_lt': 'icmp ult',
                              'char_le': 'icmp ule',
                              'char_eq': 'icmp eq',
                              'char_ne': 'icmp ne',
                              'char_ge': 'icmp uge',
                              'char_gt': 'icmp ugt'})

    def __init__(self, db, codewriter):
        self.db = db
        self.codewriter = codewriter
        self.word = db.get_machine_word()

    def _tmp(self, count=1):
        if count == 1:
            return self.db.repr_tmpvar()
        else:
            return [self.db.repr_tmpvar() for ii in range(count)]
        
    def _arrayindices(self, arg):
        ARRAYTYPE = arg.concretetype.TO
        indices = []        
        if isinstance(ARRAYTYPE, lltype.Array):
            if not ARRAYTYPE._hints.get("nolength", False):
                # skip the length field
                indices.append((self.word, 0))
                typedefnode = self.db.obj2node[ARRAYTYPE]
                indexref = typedefnode.indexref_for_items()
                indices.append((self.word, indexref))
        else:
            assert isinstance(ARRAYTYPE, lltype.FixedSizeArray)
            indices.append((self.word, 0))
        return indices

    def write_operation(self, op):
        self.codewriter.comment(str(op))
        if self.db.genllvm.config.translation.llvm.debug:
            self.codewriter.debug_print(str(op) + "\n")

        if op.opname in ("direct_call", 'indirect_call'):
            opr = OpReprCall(op, self.db)
        else:
            opr = OpRepr(op, self.db)

        if op.opname.startswith('gc'):
            meth = getattr(self.db.gcpolicy, 'op' + op.opname[2:])
            meth(self.codewriter, opr)

        elif op.opname in self.binary_operations:
            self.binaryop(opr)

        elif op.opname in self.shift_operations:
            self.shiftop(opr)

        elif op.opname.startswith('cast_') or op.opname.startswith('truncate_'):
            if op.opname in ("cast_ptr_to_int", "cast_adr_to_int"):
                self.cast_ptr_to_int(opr)
            elif op.opname in ("cast_int_to_ptr", "cast_int_to_adr"):
                self.cast_int_to_ptr(opr)
            else:
                self.cast_primitive(opr)
        elif op.opname == 'force_cast':
            self.cast_primitive(opr)
        else:
            meth = getattr(self, op.opname, None)
            if not meth:
                raise Exception, "operation %s not found" % op.opname
            meth(opr)            

        if self.db.genllvm.config.translation.llvm.debug:
            self.codewriter.newline()

    def _skipped(self, opr):
        self.codewriter.comment('***Skipping operation %s()' % opr.op.opname)
    keepalive = _skipped
    resume_point = _skipped

    def int_abs(self, opr):
        assert len(opr.argrefs) == 1
        functionref = '@pypyop_' + opr.op.opname
        self.codewriter.call(opr.retref, opr.rettype, functionref,
                             opr.argtypes, opr.argrefs)

    float_abs = int_abs
    llong_abs = int_abs

    def debug_assert(self, opr):
        # XXX could do something about assertions
        pass

    def _generic_neg(self, opr, zerostr): 
        self.codewriter.binaryop("sub", opr.retref, opr.argtypes[0],
                                 zerostr, opr.argrefs[0])

    def int_neg(self, opr):
        self._generic_neg(opr, "0")

    llong_neg = int_neg

    def float_neg(self, opr):
        self._generic_neg(opr, "0.0") 

    def bool_not(self, opr):
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "true")

    def int_invert(self, opr):
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], -1)

    def uint_invert(self, opr):
        from sys import maxint
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], str(maxint*2+1))

    def binaryop(self, opr):
        assert len(opr.argrefs) == 2
        name = self.binary_operations[opr.op.opname]
        self.codewriter.binaryop(name, opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], opr.argrefs[1])

    def shiftop(self, opr):
        op = opr.op
        name = self.shift_operations[op.opname]

        var = opr.argrefs[1]            
        self.codewriter.shiftop(name, opr.retref, opr.argtypes[0], opr.argrefs[0], var)

    def cast_primitive(self, opr):
        " works for all casts "
        totype = opr.rettype
        fromtype = opr.argtypes[0]
        to_lltype = opr.op.result.concretetype
        from_lltype = opr.op.args[0].concretetype

        def issigned(ct):
            # XXX why does size_and_sign() think lltype.Char, lltype.UniChar are signed??
            if ct in [lltype.Bool, lltype.Char, lltype.UniChar]:
                return False
            from pypy.rpython.lltypesystem.rffi import size_and_sign
            return not size_and_sign(ct)[1]

        casttype = "bitcast"

        if '*' not in fromtype:
            if fromtype[0] == 'i8':
                 assert totype[0] == 'i'
                 tosize = int(totype[1:])
                 assert tosize > 8
                 casttype = "zext" 
                     
            if fromtype[0] == 'i' and totype[0] == 'i':
                fromsize = int(fromtype[1:])
                tosize = int(totype[1:])
                if tosize > fromsize:
                    if issigned(from_lltype):
                        casttype = "sext" 
                    else:
                        casttype = "zext" 
                elif tosize < fromsize:
                    casttype = "trunc"
                else:
                    pass
            else:
                if (fromtype[0] == 'i' and totype in ['double', 'float']):
                    if issigned(from_lltype):
                        casttype = "sitofp"
                    else:
                        casttype = "uitofp"
                        
                elif (fromtype in ['double', 'float'] and totype[0] == 'i'):
                    if issigned(to_lltype):
                        casttype = "fptosi"
                    else:
                        casttype = "fptoui"
                else:
                    if fromtype != totype:
                        if fromtype == "double":
                            casttype = 'fptrunc'
                        else:
                            casttype = 'fpext'
        else:
            assert '*' in totype

        self.codewriter.cast(opr.retref, opr.argtypes[0],
                             opr.argrefs[0], opr.rettype, casttype)
    same_as = cast_primitive

    def cast_ptr_to_int(self, opr):
        self.codewriter.cast(opr.retref, opr.argtypes[0],
                             opr.argrefs[0], opr.rettype, 'ptrtoint')

    def cast_int_to_ptr(self, opr):
        self.codewriter.cast(opr.retref, opr.argtypes[0],
                             opr.argrefs[0], opr.rettype, 'inttoptr')

    def int_is_true(self, opr):
        self.codewriter.binaryop("icmp ne", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "0")
    uint_is_true = int_is_true
    llong_is_true = int_is_true
    ullong_is_true = int_is_true

    def float_is_true(self, opr):
        self.codewriter.binaryop("fcmp une", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "0.0")

    def ptr_nonzero(self, opr):
        self.codewriter.binaryop("icmp ne", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "null")

    def ptr_iszero(self, opr):
        self.codewriter.binaryop("icmp eq", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "null")

    def direct_call(self, opr):
        rettype_attrs = ""

        # XXX aargh - more illegal fishing
        # XXX sort this out later...
        arg = opr.op.args[0]
        from pypy.objspace.flow.model import Constant
        if isinstance(arg, Constant):
            T = arg.concretetype.TO
            assert isinstance(T, lltype.FuncType)
            value = opr.op.args[0].value._obj        
            if getattr(value, 'external', None) == 'C':
                rettype_attrs = self.db.primitives.get_attrs_for_type(T.RESULT)
            
        self.codewriter.call(opr.retref, opr.rettype, opr.argrefs[0],
                             opr.argtypes[1:], opr.argrefs[1:], ret_type_attrs=rettype_attrs)

    # the following works since the extra arguments that indirect_call has
    # is of type Void, which is removed by direct_call
    indirect_call = direct_call

    def boehm_malloc(self, opr):
        self.db.gcpolicy._zeromalloc(self.codewriter, opr.retref, opr.argrefs[0], atomic=False)

    def boehm_malloc_atomic(self, opr):
        self.db.gcpolicy._zeromalloc(self.codewriter, opr.retref, opr.argrefs[0], atomic=True)

    def boehm_register_finalizer(self, opr):
        tmpvar = self._tmp()
        self.codewriter.cast(tmpvar, opr.argtypes[1], opr.argrefs[1], 'i8 *')
        self.codewriter.call(None, 'void', '@pypy_register_finalizer',  ['i8 *', 'i8 *'], [opr.argrefs[0], tmpvar])

    def boehm_disappearing_link(self, opr):
        self.codewriter.call(None, 'void', '@pypy_disappearing_link', ['i8 *', 'i8 *'], [opr.argrefs[0], opr.argrefs[1]])

    def call_boehm_gc_alloc(self, opr):
        word = self.db.get_machine_word()
        self.codewriter.call(opr.retref, 'i8*', '@pypy_malloc',
                             [word], [opr.argrefs[0]])

    def to_getelementptr(self, TYPE, args):
        if isinstance(TYPE, lltype.Array) and TYPE._hints.get("nolength", False):
            indices = []
        else:
            indices = [("i32", 0)]
        for arg in args:
            typedefnode = self.db.obj2node[TYPE]
            if arg.concretetype is lltype.Void:
                # access via a field name
                name = arg.value
                TYPE = typedefnode.fieldname_to_getelementptr(indices, name)
            else:
                # access via an array index
                indexref = self.db.repr_arg(arg)
                TYPE = typedefnode.indexref_to_getelementptr(indices, indexref)

        return TYPE, indices

    def getinteriorfield(self, opr):
        if opr.rettype != "void":
            op = opr.op
            _, indices = self.to_getelementptr(op.args[0].concretetype.TO, op.args[1:])
            tmpvar = self._tmp()
            self.codewriter.getelementptr(tmpvar, opr.argtypes[0], opr.argrefs[0], indices, getptr=False)
            self.codewriter.load(opr.retref, opr.rettype, tmpvar)
        else:
            self._skipped(opr)

    # struct, name
    getfield = getinteriorfield
    # array, index | fixedsizearray index/name 
    getarrayitem = getinteriorfield  

    def _getinteriorpointer(self, opr):
        assert opr.rettype != "void"
        op = opr.op
        _, indices = self.to_getelementptr(op.args[0].concretetype.TO, op.args[1:])
        self.codewriter.getelementptr(opr.retref, opr.argtypes[0], opr.argrefs[0], indices, getptr=False)

    # struct, name
    getsubstruct = _getinteriorpointer
    # array, index | fixedsizearray, index/name
    getarraysubstruct = _getinteriorpointer  

    def setinteriorfield(self, opr):
        op = opr.op
        if opr.argtypes[-1] != "void":
            _, indices = self.to_getelementptr(op.args[0].concretetype.TO, op.args[1:-1])
            tmpvar = self._tmp()
            self.codewriter.getelementptr(tmpvar, opr.argtypes[0], opr.argrefs[0], indices, getptr=False)
            self.codewriter.store(opr.argtypes[-1], opr.argrefs[-1], tmpvar)
        else:
            self._skipped(opr)            

    bare_setinteriorfield = setinteriorfield
    # struct, name, value
    bare_setfield = setfield = setinteriorfield 
    # array, index, value | fixedsizearray, index/name, value
    bare_setarrayitem = setarrayitem = setinteriorfield 

    def getinteriorarraysize(self, opr):
        op = opr.op
        TYPE, indices = self.to_getelementptr(op.args[0].concretetype.TO, op.args[1:])
        if isinstance(TYPE, lltype.Array):
            assert not TYPE._hints.get("nolength", False) 
            # gets the length
            typedefnode = self.db.obj2node[TYPE]
            indexref = typedefnode.indexref_for_length()
            indices.append(("i32", indexref))
            lengthref = self._tmp()
            self.codewriter.getelementptr(lengthref, opr.argtypes[0], opr.argrefs[0], indices, getptr=False)
        else:
            assert False, "known at compile time"

        self.codewriter.load(opr.retref, opr.rettype, lengthref)

    # array | fixedsizearray
    getarraysize = getinteriorarraysize

    def direct_fieldptr(self, opr):        
        from pypy.translator.llvm.typedefnode import getindexhelper
        
        op = opr.op
        assert opr.rettype != "void"
        index = getindexhelper(self.db,
                               op.args[1].value,
                               op.args[0].concretetype.TO)
        assert index != -1
        tmpvar = self._tmp()
        self.codewriter.getelementptr(tmpvar, opr.argtypes[0],
                                      opr.argrefs[0], [(self.word, index)])

        # getelementptr gets a pointer to the right type, except the generated code really expected 
        # an array of size 1... so we just cast it
        element_type = self.db.repr_type(op.result.concretetype.TO.OF) + '*'
        self.codewriter.cast(opr.retref, element_type, tmpvar, opr.rettype)

    def direct_arrayitems(self, opr):
        assert opr.rettype != "void"

        array = opr.argrefs[0]
        arraytype = opr.argtypes[0]
        indices = self._arrayindices(opr.op.args[0]) + [(self.word, 0)]
        tmpvar = self._tmp()
        self.codewriter.getelementptr(tmpvar, arraytype, array, indices, getptr=False)

        # getelementptr gets a pointer to the right type, except the generated code really expected 
        # an array of size 1... so we just cast it
        element_type = self.db.repr_type(opr.op.result.concretetype.TO.OF) + '*'
        self.codewriter.cast(opr.retref, element_type, tmpvar, opr.rettype)

    def direct_ptradd(self, opr):
        array, incr = opr.argrefs
        arraytype, _ = opr.argtypes
        
        tmpvar = self._tmp()

        indices = []
        ARRAY = opr.op.args[0].concretetype.TO
        if not (isinstance(ARRAY, lltype.Array) and ARRAY._hints.get("nolength", False)):
            indices.append( (self.word, 0))
        indices.append((self.word, incr))
        self.codewriter.getelementptr(tmpvar, arraytype, array, indices, getptr=False)

        # getelementptr gets a pointer to the right type, except the generated code really expected 
        # an array of size 1... so we just cast it
        element_type = self.db.repr_type(opr.op.result.concretetype.TO.OF) + '*'
        self.codewriter.cast(opr.retref, element_type, tmpvar, opr.rettype)

    def adr_delta(self, opr):
        addr1, addr2 = self._tmp(2)
        self.codewriter.cast(addr1, opr.argtypes[0], opr.argrefs[0], self.word, 'ptrtoint')
        self.codewriter.cast(addr2, opr.argtypes[1], opr.argrefs[1], self.word, 'ptrtoint')
        self.codewriter.binaryop("sub", opr.retref, opr.rettype, addr1, addr2)

    def _op_adr_generic(self, opr, llvm_op):
        addr, res = self._tmp(2)

        self.codewriter.cast(addr, opr.argtypes[0], opr.argrefs[0], self.word, 'ptrtoint')
        self.codewriter.binaryop(llvm_op, res, self.word, addr, opr.argrefs[1])
        self.codewriter.cast(opr.retref, self.word, res, opr.rettype, 'inttoptr')

    def adr_add(self, opr):
        self._op_adr_generic(opr, "add")

    def adr_sub(self, opr):
        self._op_adr_generic(opr, "sub")

    def _op_adr_cmp(self, opr, llvm_op):
        addr1, addr2 = self._tmp(2)
        self.codewriter.cast(addr1, opr.argtypes[0], opr.argrefs[0], self.word, 'ptrtoint')
        self.codewriter.cast(addr2, opr.argtypes[1], opr.argrefs[1], self.word, 'ptrtoint')
        assert opr.rettype == "i1"
        self.codewriter.binaryop(llvm_op, opr.retref, self.word, addr1, addr2)

    def adr_eq(self, opr):
        self._op_adr_cmp(opr, "icmp eq")

    def adr_ne(self, opr):
        self._op_adr_cmp(opr, "icmp ne")

    def adr_le(self, opr):
        self._op_adr_cmp(opr, "icmp sle")

    def adr_gt(self, opr):
        self._op_adr_cmp(opr, "icmp sgt")

    def adr_lt(self, opr):
        self._op_adr_cmp(opr, "icmp slt")

    def adr_ge(self, opr):
        self._op_adr_cmp(opr, "icmp sge")

    def raw_malloc(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "@raw_malloc",
                             opr.argtypes, opr.argrefs)

    def raw_malloc_usage(self, opr):
        self.codewriter.cast(opr.retref, opr.argtypes[0], opr.argrefs[0],
                             opr.rettype)

    def raw_free(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "@raw_free",
                             opr.argtypes, opr.argrefs)

    def raw_memcopy(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "@raw_memcopy",
                             opr.argtypes, opr.argrefs)

    def raw_memclear(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "@raw_memclear",
                             opr.argtypes, opr.argrefs)

    def raw_store(self, opr):
        arg_addr, arg_dummy, arg_incr, arg_value = opr.argrefs
        (argtype_addr, argtype_dummy,
         argtype_incr, argtype_value) = opr.argtypes

        cast_addr = self._tmp()
        addr_type = argtype_value + "*"

        # cast to the correct type before arithmetic/storing
        self.codewriter.cast(cast_addr, argtype_addr, arg_addr, addr_type)

        # pointer arithmetic
        if arg_incr:
            incr_addr = self._tmp()
            self.codewriter.getelementptr(incr_addr,
                                          addr_type,
                                          cast_addr,
                                          [(self.word, arg_incr)],
                                          getptr=False)
            cast_addr = incr_addr
        self.codewriter.store(argtype_value, arg_value, cast_addr)

        
    def raw_load(self, opr):
        arg_addr, arg_dummy, arg_incr = opr.argrefs
        argtype_addr, argtype_dummy, argtype_incr = opr.argtypes

        cast_addr = self._tmp()
        addr_type = opr.rettype + "*"

        # cast to the correct type before arithmetic/loading
        self.codewriter.cast(cast_addr, argtype_addr, arg_addr, addr_type)

        # pointer arithmetic
        if arg_incr:
            incr_addr = self._tmp()
            self.codewriter.getelementptr(incr_addr,
                                          addr_type,
                                          cast_addr,
                                          [(self.word, arg_incr)],
                                          getptr=False)
            cast_addr = incr_addr

        self.codewriter.load(opr.retref, opr.rettype, cast_addr) 

    def debug_print(self, opr):
        pass     # XXX

    def debug_fatalerror(self, opr):
        # XXX message?
        self.codewriter.call(None, "void", "@abort", [], [])

    def hint(self, opr):
        self.same_as(opr)

    def is_early_constant(self, opr):
        # If it gets this far it is always false
        self.codewriter.cast(opr.retref, 'i1', 'false', opr.rettype)

    def debug_llinterpcall(self, opr):
        self.codewriter.call(None, "void", "@abort", [], [])
        # cheat llvm
        self.codewriter.cast(opr.retref, opr.rettype, 'undef', opr.rettype)

    # ____________________________________________________________
    # Special support for llvm.gcroot

    def llvm_store_gcroot(self, opr):
        index = opr.op.args[0].value
        rootref = '%%gcroot%d' % index
        var = self.db.repr_tmpvar()
        self.codewriter.cast(var, opr.argtypes[1], opr.argrefs[1], 'i8*')
        self.codewriter.store('i8*', var, rootref)

    def llvm_load_gcroot(self, opr):
        index = opr.op.args[0].value
        rootref = '%%gcroot%d' % index
        self.codewriter.load(opr.retref, opr.rettype, rootref)

    def llvm_frameaddress(self, opr):
        self.codewriter.call(opr.retref, opr.rettype,
                             "@llvm.frameaddress", ['i32'], ['0'])

    def llvm_gcmapstart(self, opr):
        self.codewriter.cast(opr.retref, 'i8*', '@__gcmapstart', opr.rettype)

    def llvm_gcmapend(self, opr):
        self.codewriter.cast(opr.retref, 'i8*', '@__gcmapend', opr.rettype)
