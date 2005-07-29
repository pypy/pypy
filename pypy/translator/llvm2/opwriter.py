import py
from pypy.objspace.flow.model import Constant
from pypy.rpython import lltype
from pypy.translator.llvm2.atomic import is_atomic
from pypy.translator.llvm2.log import log 
log = log.opwriter

class OpWriter(object):
    binary_operations = {'int_mul': 'mul',
                         'int_add': 'add',
                         'int_sub': 'sub',
                         'int_floordiv': 'div',
                         'int_mod': 'rem',
                         'int_and': 'and',
                         'int_or': 'or',
                         'int_xor': 'xor',
                         'int_lt': 'setlt',
                         'int_le': 'setle',
                         'int_eq': 'seteq',
                         'int_ne': 'setne',
                         'int_ge': 'setge',
                         'int_gt': 'setgt',

                         'uint_mul': 'mul',
                         'uint_add': 'add',
                         'uint_sub': 'sub',
                         'uint_floordiv': 'div',
                         'uint_mod': 'rem',
                         'uint_and': 'and',
                         'uint_or': 'or',
                         'uint_xor': 'xor',
                         'uint_lt': 'setlt',
                         'uint_le': 'setle',
                         'uint_eq': 'seteq',
                         'uint_ne': 'setne',
                         'uint_ge': 'setge',
                         'uint_gt': 'setgt',

                         'char_lt': 'setlt',
                         'char_le': 'setle',
                         'char_eq': 'seteq',
                         'char_ne': 'setne',
                         'char_ge': 'setge',
                         'char_gt': 'setgt',

                         'float_mul': 'mul',
                         'float_add': 'add',
                         'float_sub': 'sub',
                         'float_truediv': 'div',
                         'float_mod': 'rem',
                         'float_lt': 'setlt',
                         'float_le': 'setle',
                         'float_eq': 'seteq',
                         'float_ne': 'setne',
                         'float_ge': 'setge',
                         'float_gt': 'setgt',

                         'ptr_eq': 'seteq',
                         'ptr_ne': 'setne',
                         }

    shift_operations  = {'int_lshift': 'shl',
                         'int_rshift': 'shr',

                         'uint_lshift': 'shl',
                         'uint_rshift': 'shr',
                         }

    def __init__(self, db, codewriter, node, block):
        self.db = db
        self.codewriter = codewriter
        self.node = node
        self.block = block

    def write_operation(self, op):
        if op.opname in self.binary_operations:
            self.binaryop(op)
        elif op.opname in self.shift_operations:
            self.shiftop(op)
        else:
            meth = getattr(self, op.opname, None)
            assert meth is not None, "operation %r not found" %(op.opname,)
            meth(op)    

    def int_neg(self, op): 
        self.codewriter.binaryop("sub", 
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 "0", 
                                 self.db.repr_arg(op.args[0]),
                                 )

    def bool_not(self, op):
        self.codewriter.binaryop("xor",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]), 
                                 "true")

                    
    def binaryop(self, op):
        name = self.binary_operations[op.opname]
        assert len(op.args) == 2
        self.codewriter.binaryop(name,
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 self.db.repr_arg(op.args[1]))

    def shiftop(self, op):
        name = self.shift_operations[op.opname]
        assert len(op.args) == 2
        if isinstance(op.args[1], Constant):
            tmpvar = self.db.repr_arg(op.args[1])
        else:
            tmpvar = self.db.repr_tmpvar()
            self.codewriter.cast(tmpvar, self.db.repr_arg_type(op.args[1]), self.db.repr_arg(op.args[1]), 'ubyte')
        self.codewriter.shiftop(name,
                                self.db.repr_arg(op.result),
                                self.db.repr_arg_type(op.args[0]),
                                self.db.repr_arg(op.args[0]),
                                tmpvar)

    def cast_primitive(self, op): #works for all primitives
        assert len(op.args) == 1
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        fromvar = self.db.repr_arg(op.args[0])
        fromtype = self.db.repr_arg_type(op.args[0])
        self.codewriter.cast(targetvar, fromtype, fromvar, targettype)

    cast_bool_to_char = cast_bool_to_int  = cast_bool_to_uint = cast_primitive
    cast_char_to_bool = cast_char_to_int  = cast_char_to_uint = cast_primitive
    cast_int_to_bool  = cast_int_to_char  = cast_int_to_uint  = cast_primitive
    cast_uint_to_bool = cast_uint_to_char = cast_uint_to_int  = cast_primitive
    cast_pointer = cast_primitive
    same_as = cast_primitive

    def int_is_true(self, op):
        self.codewriter.binaryop("setne",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "0")
    uint_is_true = int_is_true

    def float_is_true(self, op):
        self.codewriter.binaryop("setne",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "0.0")

    def ptr_nonzero(self, op):
        self.codewriter.binaryop("setne",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "null")

    def ptr_iszero(self, op):
        self.codewriter.binaryop("seteq",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]),
                                 "null")

    def direct_call(self, op):
        assert len(op.args) >= 1
        targetvar = self.db.repr_arg(op.result)
        returntype = self.db.repr_arg_type(op.result)
        functionref = self.db.repr_arg(op.args[0])
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])
        if returntype != "void":
            self.codewriter.call(targetvar, returntype, functionref, argrefs,
                                 argtypes)
        else:
            self.codewriter.call_void(functionref, argrefs, argtypes)

    def direct_invoke(self, op):
        assert len(op.args) >= 1
        assert len(self.block.exits) >= 2   #at least one label and one exception label

        link = self.block.exits[0]
        assert link.exitcase is None

        targetvar = self.db.repr_arg(op.result)
        returntype = self.db.repr_arg_type(op.result)
        functionref = self.db.repr_arg(op.args[0])
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])

        none_label      = self.node.block_to_name[link.target]
        exc_label       = self.node.block_to_name[self.block] + '_exception'
        exc_error_label = exc_label + '_error'

        if returntype != "void":
            self.codewriter.invoke(targetvar, returntype, functionref, argrefs,
                                 argtypes, none_label, exc_label)
        else:
            self.codewriter.invoke_void(functionref, argrefs, argtypes, none_label, exc_label)

        self.codewriter.label(exc_label)
        value_label = []
        value = 0
        for link in self.block.exits[1:]:
            assert issubclass(link.exitcase, Exception)

            target = self.node.block_to_name[link.target]
            value_label.append( (value,target) )
            value += 1

            #msg = 'XXX Exception target=%s, exitcase=%s, last_exception.concretetype=%s' % \
            #    (str(target), str(link.exitcase), link.last_exception.concretetype)
            #self.codewriter.comment(msg)
            #self.codewriter.comment('TODO: in %s rename %s to %s' % (target, self.node.block_to_name[self.block], exc_label))

        tmptype1, tmpvar1 = 'long'                , self.db.repr_tmpvar()
        self.codewriter.load(tmpvar1, tmptype1, '%last_exception_type')

        #tmptype2, tmpvar2 = '%structtype.object_vtable*', self.db.repr_tmpvar()
        #self.codewriter.cast(tmpvar2, tmptype1, tmpvar1, tmptype2)
        #self.codewriter.switch(tmptype2, tmpvar2, exc_error_label, value_label)

        #XXX get helper function name
        exceptiondata      = self.db._translator.rtyper.getexceptiondata()
        
        #functions
        ll_exception_match = exceptiondata.ll_exception_match.__name__
        #yield ('RPYTHON_EXCEPTION_MATCH',  exceptiondata.ll_exception_match)
        #yield ('RPYTHON_TYPE_OF_EXC_INST', exceptiondata.ll_type_of_exc_inst)
        #yield ('RPYTHON_PYEXCCLASS2EXC',   exceptiondata.ll_pyexcclass2exc)
        #yield ('RAISE_OSERROR',            exceptiondata.ll_raise_OSError)

        #datatypes
        lltype_of_exception_type  = 'structtype.' + exceptiondata.lltype_of_exception_type.TO.__name__
        lltype_of_exception_value = 'structtype.' + exceptiondata.lltype_of_exception_value.TO.__name__
        #yield ('RPYTHON_EXCEPTION_VTABLE', exceptiondata.lltype_of_exception_type)
        #yield ('RPYTHON_EXCEPTION',        exceptiondata.lltype_of_exception_value)

        self.codewriter.newline()
        self.codewriter.comment('HERE')
        self.codewriter.comment(ll_exception_match)         #ll_issubclass__object_vtablePtr_object_vtablePtr
        self.codewriter.comment(lltype_of_exception_type)   #
        self.codewriter.comment(lltype_of_exception_value)  #
        self.codewriter.newline()

        self.codewriter.switch(tmptype1, tmpvar1, exc_error_label, value_label)
        self.codewriter.label(exc_error_label)
        self.codewriter.comment('dead code ahead')
        self.codewriter.ret('int', '0')
        #self.codewriter.unwind()   #this causes llvm to crash?!?

    def malloc(self, op): 
        targetvar = self.db.repr_arg(op.result) 
        arg = op.args[0]
        assert (isinstance(arg, Constant) and 
                isinstance(arg.value, lltype.Struct))
        #XXX unclean
        node  = self.db.obj2node[arg.value]
        type_ = node.ref
        self.codewriter.malloc(targetvar, type_, atomic=is_atomic(node)) 

    def malloc_varsize(self, op):
        targetvar = self.db.repr_arg(op.result)
        arg_type = op.args[0]
        assert (isinstance(arg_type, Constant) and 
                isinstance(arg_type.value, (lltype.Array, lltype.Struct)))
        #XXX unclean
        struct_type = self.db.obj2node[arg_type.value].ref
        struct_cons = self.db.obj2node[arg_type.value].constructor_ref
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])
        self.codewriter.call(targetvar, struct_type + "*", struct_cons,
                             argrefs, argtypes)

    def getfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        fieldnames = list(op.args[0].concretetype.TO._names)
        index = fieldnames.index(op.args[1].value)
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        if targettype != "void":
            self.codewriter.getelementptr(tmpvar, structtype, struct,
                                          ("uint", index))        
            self.codewriter.load(targetvar, targettype, tmpvar)
        else:
            self.codewriter.comment("***Skipping operation getfield()***")
 
    def getsubstruct(self, op): 
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        fieldnames = list(op.args[0].concretetype.TO._names)
        index = fieldnames.index(op.args[1].value)
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        assert targettype != "void"
        self.codewriter.getelementptr(targetvar, structtype, 
                                      struct, ("uint", index))        
         
    def setfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        fieldnames = list(op.args[0].concretetype.TO._names)
        index = fieldnames.index(op.args[1].value)
        self.codewriter.getelementptr(tmpvar, structtype, struct,
                                      ("uint", index))
        valuevar, valuetype = self.db.repr_argwithtype(op.args[2])
        assert valuetype != "void"
        self.codewriter.store(valuetype, valuevar, tmpvar) 

    def getarrayitem(self, op):        
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])
        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, arraytype, array,
                                      ("uint", 1), (indextype, index))
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        self.codewriter.load(targetvar, targettype, tmpvar)

    def getarraysubstruct(self, op):        
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])
        targetvar = self.db.repr_arg(op.result)
        self.codewriter.getelementptr(targetvar, arraytype, array,
                                      ("uint", 1), (indextype, index))

    def setarrayitem(self, op):
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])

        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, arraytype, array,
                                      ("uint", 1), (indextype, index))

        valuevar = self.db.repr_arg(op.args[2]) 
        valuetype = self.db.repr_arg_type(op.args[2])
        self.codewriter.store(valuetype, valuevar, tmpvar) 

    def getarraysize(self, op):
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, arraytype, array, ("uint", 0))
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        self.codewriter.load(targetvar, targettype, tmpvar)
