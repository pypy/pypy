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

class OpReprInvoke(OpReprCall):
    __slots__ = "db op retref rettype argrefs argtypes functionref".split()
    def __init__(self, op, db):
        super(OpReprInvoke, self).__init__(op, db)
        
        if op.opname in ('direct_call', 'indirect_call'):
            self.functionref = self.argrefs[0]
            self.argrefs = self.argrefs[1:]
            self.argtypes = self.argtypes[1:]            
        else:
            self.functionref = '%pypyop_' + op.opname

class OpWriter(object):            
    
    binary_operations = {
        'float_mul'     : 'mul',
        'float_add'     : 'add',
        'float_sub'     : 'sub',
        'float_truediv' : 'div',
        
        'ptr_eq'        : 'seteq',
        'ptr_ne'        : 'setne' }

    # generic numeric ops
    for tt in 'int llong uint'.split():
        for oo in 'mul add sub and or xor'.split():
            binary_operations['%s_%s' % (tt, oo)] = oo
        binary_operations['%s_floordiv' % tt] = 'div'
        binary_operations['%s_mod' % tt] = 'rem'

    # comparison ops
    for tt in 'int llong uint unichar float'.split():
        for oo in 'lt le eq ne ge gt'.split():
            binary_operations['%s_%s' % (tt, oo)] = 'set%s' % oo


    shift_operations = {'int_lshift': 'shl',
                        'int_rshift': 'shr',
                        
                        'uint_lshift': 'shl',
                        'uint_rshift': 'shr',
                        
                        'llong_lshift': 'shl',
                        'llong_rshift': 'shr',
                         }

    char_operations = {'char_lt': 'setlt',
                       'char_le': 'setle',
                       'char_eq': 'seteq',
                       'char_ne': 'setne',
                       'char_ge': 'setge',
                       'char_gt': 'setgt'}

    def __init__(self, db, codewriter):
        self.db = db
        self.codewriter = codewriter

    def _tmp(self, count=1):
        if count == 1:
            return self.db.repr_tmpvar()
        else:
            return [self.db.repr_tmpvar() for ii in range(count)]
        
    def write_operation(self, op):
        if op.opname in ("direct_call", 'indirect_call'):
            opr = OpReprCall(op, self.db)
        else:
            opr = OpRepr(op, self.db)

        if op.opname in self.binary_operations:
            self.binaryop(opr)
        elif op.opname in self.shift_operations:
            self.shiftop(opr)
        elif op.opname in self.char_operations:
            self.char_binaryop(opr)
        elif op.opname.startswith('cast_') or op.opname.startswith('truncate_'):
            if op.opname == 'cast_char_to_int':
                self.cast_char_to_int(opr)
            else:
                self.cast_primitive(opr)
        else:
            meth = getattr(self, op.opname, None)
            if not meth:
                raise Exception, "operation %s not found" % op.opname
            meth(opr)            

    def write_invoke_op(self, op, node, block):
        opr = OpReprInvoke(op, self.db)
        ep = self.db.exceptionpolicy
        ep.invoke(self.codewriter, opr.retref, opr.rettype, opr.functionref,
                  opr.argrefs, opr.argtypes, node, block)
    
    def _generic_pow(self, opr, onestr): 

        # XXX This broken as... will only work for constants
        try:
            value = "NO VALUE"
            value = opr.op.args[1].value
            operand = int(value)
        except Exception, exc:
            msg = 'XXX: Error: _generic_pow: Variable '\
                  '%s - failed to convert to int %s' % (value, str(exc))
            self.codewriter.comment(msg)
            raise Exception(msg)

        mult_type = opr.argtypes[0]
        mult_val = opr.argrefs[0]
        last_val = mult_val
        
        if operand < 1:
            res_val = onestr
        else:
            res_val = mult_val
            for ii in range(operand - 1):
                res_val = self._tmp()
                self.codewriter.binaryop("mul", res_val, mult_type,
                                         last_val, mult_val)
                last_val = res_val
        self.codewriter.cast(opr.retref, mult_type, res_val, mult_type)        

    def _skipped(self, opr):
        self.codewriter.comment('***Skipping operation %s()' % opr.op.opname)
    keepalive = _skipped

    def int_abs(self, opr):
        assert len(opr.argrefs) == 1
        functionref = '%pypyop_' + opr.op.opname
        self.codewriter.call(opr.retref, opr.rettype, functionref,
                             opr.argtypes, opr.argrefs)

    float_abs = int_abs
    llong_abs = int_abs

    def int_pow(self, opr):
        self._generic_pow(opr, "1") 
    uint_pow = int_pow
    
    def float_pow(self, opr):
        self._generic_pow(opr, "1.0") 

    def _generic_neg(self, opr, zerostr): 
        self.codewriter.binaryop("sub", opr.retref, opr.argtypes[0],
                                 zerostr, opr.argrefs[0])

    def int_neg(self, opr):
        self._generic_neg(opr, "0")

    # this is really generated, don't know why
    # XXX rxe: Surely that cant be right?
    uint_neg = int_neg

    def float_neg(self, opr):
        self._generic_neg(opr, "0.0") 

    def bool_not(self, opr):
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "true")

    def int_invert(self, opr):
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], -1)

    def uint_invert(self, opr):
        self.codewriter.binaryop("xor", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], str((1L<<32) - 1))

    def binaryop(self, opr):
        assert len(opr.argrefs) == 2
        name = self.binary_operations[opr.op.opname]
        self.codewriter.binaryop(name, opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], opr.argrefs[1])

    def char_binaryop(self, opr):
        assert len(opr.argrefs) == 2
        name = self.char_operations[opr.op.opname]
        c1, c2 = self._tmp(2)
        self.codewriter.cast(c1, "sbyte", opr.argrefs[0], "ubyte")
        self.codewriter.cast(c2, "sbyte", opr.argrefs[1], "ubyte")
        self.codewriter.binaryop(name, opr.retref, "ubyte", c1, c2)

    def shiftop(self, opr):
        op = opr.op
        name = self.shift_operations[op.opname]

        if isinstance(op.args[1], Constant):
            var = opr.argrefs[1]
        else:
            var = self._tmp()
            self.codewriter.cast(var, opr.argtypes[1], opr.argrefs[1], 'ubyte')
            
        self.codewriter.shiftop(name, opr.retref, opr.argtypes[0],
                                opr.argrefs[0], var)

    def cast_char_to_int(self, opr):
        " works for all casts "
        assert len(opr.argrefs) == 1
        intermediate = self._tmp()
        self.codewriter.cast(intermediate, opr.argtypes[0],
                             opr.argrefs[0], "ubyte")
        self.codewriter.cast(opr.retref, "ubyte", intermediate, opr.rettype)

    def cast_primitive(self, opr):
        " works for all casts "
        assert len(opr.argrefs) == 1
        self.codewriter.cast(opr.retref, opr.argtypes[0],
                             opr.argrefs[0], opr.rettype)
    same_as = cast_primitive

    def int_is_true(self, opr):
        self.codewriter.binaryop("setne", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "0")
    uint_is_true = int_is_true
    llong_is_true = int_is_true

    def float_is_true(self, opr):
        self.codewriter.binaryop("setne", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "0.0")

    def ptr_nonzero(self, opr):
        self.codewriter.binaryop("setne", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "null")

    def ptr_iszero(self, opr):
        self.codewriter.binaryop("seteq", opr.retref, opr.argtypes[0],
                                 opr.argrefs[0], "null")

    def direct_call(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, opr.argrefs[0],
                             opr.argtypes[1:], opr.argrefs[1:])

    indirect_call = direct_call # XXX for now

    def malloc(self, opr):
        arg_type = opr.op.args[0].value
        self.db.gcpolicy.malloc(self.codewriter, opr.retref, opr.rettype,
                                atomic=arg_type._is_atomic())

    def malloc_varsize(self, opr):

        # XXX transformation
        arg_type = opr.op.args[0].value
        if isinstance(arg_type, lltype.Array) and arg_type.OF is lltype.Void:
            # This is a backend decision to NOT represent a void array with
            # anything and save space - therefore not varsized anymore
            self.malloc(opr)
            return

        self.codewriter.call(opr.retref, opr.rettype,
                             self.db.repr_constructor(arg_type),
                             opr.argtypes[1:], opr.argrefs[1:])

    def _getindexhelper(self, name, struct):
        assert name in list(struct._names)

        fieldnames = struct._names_without_voids()
        try:
            index = fieldnames.index(name)
        except ValueError:
            index = -1
        return index

    def getfield(self, opr):
        op = opr.op
        if opr.rettype != "void":
            index = self._getindexhelper(op.args[1].value,
                                         op.args[0].concretetype.TO)
            assert index != -1
            tmpvar = self._tmp()
            self.codewriter.getelementptr(tmpvar, opr.argtypes[0],
                                          opr.argrefs[0], [("uint", index)])
            self.codewriter.load(opr.retref, opr.rettype, tmpvar)
        else:
            self._skipped(opr)
 
    def getsubstruct(self, opr): 
        index = self._getindexhelper(opr.op.args[1].value,
                                     opr.op.args[0].concretetype.TO)
        assert opr.rettype != "void"
        self.codewriter.getelementptr(opr.retref, opr.argtypes[0], 
                                      opr.argrefs[0], [("uint", index)])        
         
    def setfield(self, opr): 
        op = opr.op
        if opr.argtypes[2] != "void":
            tmpvar = self._tmp()
            index = self._getindexhelper(op.args[1].value,
                                         op.args[0].concretetype.TO)
            self.codewriter.getelementptr(tmpvar, opr.argtypes[0],
                                          opr.argrefs[0], [("uint", index)])
            self.codewriter.store(opr.argtypes[2], opr.argrefs[2], tmpvar)

        else:
            self._skipped(opr)
            
    def getarrayitem(self, opr):        
        if opr.rettype != "void":
            arraytype, indextype = opr.argtypes
            array, index = opr.argrefs
            tmpvar = self._tmp()
            self.codewriter.getelementptr(tmpvar, arraytype, array,
                                          [("uint", 1), (indextype, index)])
            self.codewriter.load(opr.retref, opr.rettype, tmpvar)
        else:
            self._skipped(opr)

    def getarraysubstruct(self, opr):        
        arraytype, indextype = opr.argtypes
        array, index = opr.argrefs
        self.codewriter.getelementptr(opr.retref, arraytype, array,
                                      [("uint", 1), (indextype, index)])

    def setarrayitem(self, opr):
        array, index, valuevar = opr.argrefs
        arraytype, indextype, valuetype = opr.argtypes
        tmpvar = self._tmp()
        if valuetype != "void":
            self.codewriter.getelementptr(tmpvar, arraytype, array,
                                          [("uint", 1), (indextype, index)])
            self.codewriter.store(valuetype, valuevar, tmpvar) 
        else:
            self._skipped(opr)

    def getarraysize(self, opr):
        tmpvar = self._tmp()
        self.codewriter.getelementptr(tmpvar, opr.argtypes[0],
                                      opr.argrefs[0], [("uint", 0)])
        self.codewriter.load(opr.retref, opr.rettype, tmpvar)

        
    # XXX use machine word size
    
    def adr_delta(self, opr):
        addr1, addr2 = self._tmp(2)
        self.codewriter.cast(addr1, opr.argtypes[0], opr.argrefs[0], "int")
        self.codewriter.cast(addr2, opr.argtypes[1], opr.argrefs[1], "int")
        self.codewriter.binaryop("sub", opr.retref, opr.rettype, addr1, addr2)

    def _op_adr_generic(self, opr, llvm_op):
        addr, res = self._tmp(2)
        self.codewriter.cast(addr, opr.argtypes[0], opr.argrefs[0], "int")
        self.codewriter.binaryop(llvm_op, res, "int", addr, opr.argrefs[1])
        self.codewriter.cast(opr.retref, "int", res, opr.rettype)

    def adr_add(self, opr):
        self._op_adr_generic(opr, "add")

    def adr_sub(self, opr):
        self._op_adr_generic(opr, "sub")

    def _op_adr_cmp(self, opr, llvm_op):
        addr1, addr2 = self._tmp(2)
        self.codewriter.cast(addr1, opr.argtypes[0], opr.argrefs[0], "int")
        self.codewriter.cast(addr2, opr.argtypes[1], opr.argrefs[1], "int")
        assert opr.rettype == "bool"
        self.codewriter.binaryop(llvm_op, opr.retref, "int", addr1, addr2)

    def adr_eq(self, opr):
        self._op_adr_cmp(opr, "seteq")

    def adr_ne(self, opr):
        self._op_adr_cmp(opr, "setne")

    def adr_le(self, opr):
        self._op_adr_cmp(opr, "setle")

    def adr_gt(self, opr):
        self._op_adr_cmp(opr, "setgt")

    def adr_lt(self, opr):
        self._op_adr_cmp(opr, "setlt")

    def adr_ge(self, opr):
        self._op_adr_cmp(opr, "setge")

    # XXX Not sure any of this makes sense - maybe seperate policy for
    # different flavours of mallocs?  Well it depend on what happens the GC
    # developments
    def raw_malloc(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "%raw_malloc",
                             opr.argtypes, opr.argrefs)
    def raw_free(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "%raw_free",
                             opr.argtypes, opr.argrefs)

    def raw_memcopy(self, opr):
        self.codewriter.call(opr.retref, opr.rettype, "%raw_memcopy",
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
                                          [("int", arg_incr)],
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
                                          [("int", arg_incr)],
                                          getptr=False)
            cast_addr = incr_addr

        self.codewriter.load(opr.retref, opr.rettype, cast_addr) 
        
    # ______________________________________________________________________
    # 
    # XXX exception specific - move to policy?

    def malloc_exception(self, opr): 
        tmpvar1, tmpvar2, tmpvar3 = self._tmp(3)
        cw = self.codewriter
        cw.getelementptr(tmpvar1, opr.rettype, "null", [("int", 1)], getptr=False)
        cw.cast(tmpvar2, opr.rettype, tmpvar1, 'uint')
        cw.call(tmpvar3, 'sbyte*', '%malloc_exception', ['uint'], [tmpvar2])
        cw.cast(opr.retref, 'sbyte*', tmpvar3, opr.rettype)

    def last_exception_type_ptr(self, opr):
        op = opr.op
        e = self.db.translator.rtyper.getexceptiondata()
        self.codewriter.load('%' + str(op.result),
                             self.db.repr_type(e.lltype_of_exception_type),
                             '%last_exception_type')

