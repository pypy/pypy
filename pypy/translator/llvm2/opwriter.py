import py
from pypy.objspace.flow.model import Constant
from pypy.rpython import lltype
from pypy.translator.llvm2.module.extfunction import extfunctions
from pypy.translator.llvm2.extfuncnode import ExternalFuncNode
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

                         'unichar_lt': 'setlt',
                         'unichar_le': 'setle',
                         'unichar_eq': 'seteq',
                         'unichar_ne': 'setne',
                         'unichar_ge': 'setge',
                         'unichar_gt': 'setgt',

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
        invoke = op.opname.startswith('invoke:')
        if invoke:
            self.invoke(op)
        else:
            if op.opname in self.binary_operations:
                self.binaryop(op)
            elif op.opname in self.shift_operations:
                self.shiftop(op)
            elif op.opname.startswith('cast_'):
                self.cast_primitive(op)
            else:
                meth = getattr(self, op.opname, None)
                if not meth:
                    msg = "operation %s not found" %(op.opname,)
                    self.codewriter.comment('XXX: Error: ' + msg)
                    #assert meth is not None, msg
                    return
                meth(op)    

    def _generic_pow(self, op, onestr): 
        mult_type = self.db.repr_arg_type(op.args[0])
        mult_val = self.db.repr_arg(op.args[0])
        last_val = mult_val
        try:
            operand = int(op.args[1].value)
        except:
            msg = 'XXX: Error: _generic_pow: Variable has no value'
            self.codewriter.comment(msg)
            return
        if operand < 1:
            res_val = onestr
        else:
            res_val = mult_val
            for ii in range(operand - 1):
                res_val = self.db.repr_tmpvar()
                self.codewriter.binaryop("mul", 
                                         res_val,
                                         mult_type,
                                         last_val,
                                         mult_val)
                last_val = res_val
        targetvar = self.db.repr_arg(op.result)
        self.codewriter.cast(targetvar, mult_type, res_val, mult_type)        

    def int_pow(self, op):
        self._generic_pow(op, "1") 
    uint_pow = int_pow
    
    def float_pow(self, op):
        self._generic_pow(op, "1.0") 

    def _generic_neg(self, op, zerostr): 
        self.codewriter.binaryop("sub", 
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 zerostr, 
                                 self.db.repr_arg(op.args[0]),
                                 )
    def int_neg(self, op):
        self._generic_neg(op, "0") 
    uint_neg = int_neg  #this is really generates, don't know why

    def float_neg(self, op):
        self._generic_neg(op, "0.0") 

    def bool_not(self, op):
        self.codewriter.binaryop("xor",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]), 
                                 "true")

    def int_invert(self, op):
        self.codewriter.binaryop("xor",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]), 
                                 -1)

    def uint_invert(self, op):
        self.codewriter.binaryop("xor",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg_type(op.args[0]),
                                 self.db.repr_arg(op.args[0]), 
                                 str((1<<32)-1))

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
    same_as = cast_primitive

    #cast_bool_to_char  = cast_bool_to_int  = cast_bool_to_uint = cast_bool_to_float = cast_bool_to_unichar  = cast_primitive
    #cast_char_to_bool  = cast_char_to_int  = cast_char_to_uint = cast_char_to_float = cast_char_to_unichar  = cast_primitive
    #cast_int_to_bool   = cast_int_to_char  = cast_int_to_uint  = cast_int_to_float  = cast_int_to_unichar   = cast_primitive
    #cast_uint_to_bool  = cast_uint_to_char = cast_uint_to_int  = cast_uint_to_float = cast_uint_to_unichar  = cast_primitive
    #cast_float_to_bool = cast_float_to_char= cast_float_to_int = cast_float_to_uint = cast_float_to_unichar = cast_primitive
    #cast_unichar_to_bool=cast_unichar_to_char=cast_unichar_to_int=cast_unichar_to_uint=cast_unichar_to_float= cast_primitive
    #cast_pointer = cast_primitive

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

        op_args = [arg for arg in op.args
                   if arg.concretetype is not lltype.Void]

        assert len(op_args) >= 1
        targetvar = self.db.repr_arg(op.result)
        returntype = self.db.repr_arg_type(op.result)
        functionref = self.db.repr_arg(op_args[0])
        argrefs = self.db.repr_arg_multi(op_args[1:])
        argtypes = self.db.repr_arg_type_multi(op_args[1:])
        if returntype != "void":
            self.codewriter.call(targetvar, returntype, functionref, argrefs,
                                 argtypes)
        else:
            self.codewriter.call_void(functionref, argrefs, argtypes)

    def invoke(self, op):
        # XXX hack as per remove_voids()
        op_args = [arg for arg in op.args
                   if arg.concretetype is not lltype.Void]

        if op.opname == 'invoke:direct_call':
            functionref = self.db.repr_arg(op_args[0])
        else:   #operation
            opname = op.opname.split(':',1)[1]
            op_args = ['%' + opname] + op_args
            functionref = op_args[0]
            ExternalFuncNode.used_external_functions[functionref] = True
            msg = "exception raising operation %s not found" %(op.opname,)
            self.codewriter.comment('XXX: Error: ' + msg)
            #assert functionref in extfunctions, msg
        
        assert len(op_args) >= 1
        assert len(self.block.exits) >= 2   #at least one label and one exception label

        link = self.block.exits[0]
        assert link.exitcase is None

        targetvar = self.db.repr_arg(op.result)
        returntype = self.db.repr_arg_type(op.result)
        argrefs = self.db.repr_arg_multi(op_args[1:])
        argtypes = self.db.repr_arg_type_multi(op_args[1:])

        none_label  = self.node.block_to_name[link.target]
        block_label = self.node.block_to_name[self.block]
        exc_label   = block_label + '_exception_handling'

        if returntype != "void":
            self.codewriter.invoke(targetvar, returntype, functionref, argrefs,
                                   argtypes, none_label, exc_label)
        else:
            self.codewriter.invoke_void(functionref, argrefs, argtypes, none_label, exc_label)

        e = self.db._translator.rtyper.getexceptiondata()
        ll_exception_match       = '%' + e.ll_exception_match.__name__
        lltype_of_exception_type = ('%structtype.' +
                                    e.lltype_of_exception_type.TO.__name__
                                    + '*')
        lltype_of_exception_value = ('%structtype.' +
                                    e.lltype_of_exception_value.TO.__name__
                                    + '*')

        self.codewriter.label(exc_label)

        exc_found_labels, last_exception_type = [], None
        for link in self.block.exits[1:]:
            assert issubclass(link.exitcase, Exception)

            etype = self.db.obj2node[link.llexitcase._obj]
            current_exception_type = etype.get_ref()

            target          = self.node.block_to_name[link.target]
            exc_found_label = block_label + '_exception_found_branchto_' + target
            last_exc_type_var, last_exc_value_var = None, None

            for p in self.node.get_phi_data(link.target):
                arg, type_, names, blocknames = p
                for name, blockname in zip(names, blocknames):
                    if blockname != exc_found_label:
                        continue
                    #XXX might want to refactor the next few lines
                    if name.startswith('%last_exception_'):
                        last_exc_type_var = name
                    if name.startswith('%last_exc_value_'):
                        last_exc_value_var = name

            t = (exc_found_label,target,last_exc_type_var,last_exc_value_var)
            exc_found_labels.append(t)

            not_this_exception_label = block_label + '_not_exception_' + etype.ref[1:]

            if current_exception_type.find('getelementptr') == -1:  #XXX catch all (except:)
                self.codewriter.br_uncond(exc_found_label)
            else:
                if not last_exception_type:
                    last_exception_type = self.db.repr_tmpvar()
                    self.codewriter.load(last_exception_type, lltype_of_exception_type, '%last_exception_type')
                    self.codewriter.newline()
                ll_issubclass_cond = self.db.repr_tmpvar()
                self.codewriter.call(ll_issubclass_cond,
                                     'bool',
                                     ll_exception_match,
                                     [last_exception_type, current_exception_type],
                                     [lltype_of_exception_type, lltype_of_exception_type])
                self.codewriter.br(ll_issubclass_cond, not_this_exception_label, exc_found_label)

            self.codewriter.label(not_this_exception_label)

        self.codewriter.comment('reraise when exception is not caught')
        self.codewriter.unwind()

        for label, target, last_exc_type_var, last_exc_value_var in exc_found_labels:
            self.codewriter.label(label)
            if last_exc_type_var:
                self.codewriter.load(last_exc_type_var, lltype_of_exception_type, '%last_exception_type')
            if last_exc_value_var:
                self.codewriter.load(last_exc_value_var, lltype_of_exception_value, '%last_exception_value')
            
            self.codewriter.br_uncond(target)

    def malloc(self, op): 
        targetvar = self.db.repr_arg(op.result) 
        arg = op.args[0]
        assert (isinstance(arg, Constant) and 
                isinstance(arg.value, lltype.Struct))
        #XXX unclean
        node  = self.db.obj2node[arg.value]
        type_ = node.ref
        self.codewriter.malloc(targetvar, type_, atomic=node.is_atomic())

    def malloc_varsize(self, op):
        targetvar = self.db.repr_arg(op.result)
        arg_type = op.args[0]
        assert (isinstance(arg_type, Constant) and 
                isinstance(arg_type.value, (lltype.Array, lltype.Struct)))

        #XXX unclean
        node = self.db.obj2node[arg_type.value]

        #XXX AAARRRRRRRRRGFFFFFFFFFFFFGGGGGGGGGGHHHHHHHHHHHHHHHHHHHHHHH
        from pypy.translator.llvm2.arraynode import VoidArrayTypeNode
        if isinstance(node, VoidArrayTypeNode):
            type_ = node.ref
            self.codewriter.malloc(targetvar, type_, atomic=True) 
            return
        
        struct_type = node.ref
        struct_cons = node.constructor_ref
        argrefs = self.db.repr_arg_multi(op.args[1:])
        argtypes = self.db.repr_arg_type_multi(op.args[1:])
        self.codewriter.call(targetvar, struct_type + "*", struct_cons,
                             argrefs, argtypes)

    def _getindexhelper(self, name, struct):
        assert name in list(struct._names)

        fieldnames = struct._names_without_voids()
        try:
            index = fieldnames.index(name)
        except ValueError:
            index = -1
        return index

    def getfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        index = self._getindexhelper(op.args[1].value, op.args[0].concretetype.TO)
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        if targettype != "void":
            assert index != -1
            self.codewriter.getelementptr(tmpvar, structtype, struct,
                                          ("uint", index))        
            self.codewriter.load(targetvar, targettype, tmpvar)
        else:
            self.codewriter.comment("***Skipping operation getfield()***")  #XXX what if this the last operation of the exception block?
 
    def getsubstruct(self, op): 
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        index = self._getindexhelper(op.args[1].value, op.args[0].concretetype.TO)
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        assert targettype != "void"
        self.codewriter.getelementptr(targetvar, structtype, 
                                      struct, ("uint", index))        
         
    def setfield(self, op): 
        tmpvar = self.db.repr_tmpvar()
        struct, structtype = self.db.repr_argwithtype(op.args[0])
        index = self._getindexhelper(op.args[1].value, op.args[0].concretetype.TO)
        valuevar, valuetype = self.db.repr_argwithtype(op.args[2])
        if valuetype != "void": 
            self.codewriter.getelementptr(tmpvar, structtype, struct,
                                          ("uint", index))
            self.codewriter.store(valuetype, valuevar, tmpvar) 
        else:
            self.codewriter.comment("***Skipping operation setfield()***")
            
    def getarrayitem(self, op):        
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        index = self.db.repr_arg(op.args[1])
        indextype = self.db.repr_arg_type(op.args[1])
        tmpvar = self.db.repr_tmpvar()
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        if targettype != "void":
            self.codewriter.getelementptr(tmpvar, arraytype, array,
                                          ("uint", 1), (indextype, index))
            self.codewriter.load(targetvar, targettype, tmpvar)
        else:
            self.codewriter.comment("***Skipping operation getarrayitem()***")

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

        valuevar = self.db.repr_arg(op.args[2]) 
        valuetype = self.db.repr_arg_type(op.args[2])
        #XXX These should skip too if the case comes up
        if valuetype != "void":
            self.codewriter.getelementptr(tmpvar, arraytype, array,
                                      ("uint", 1), (indextype, index))
            self.codewriter.store(valuetype, valuevar, tmpvar) 
        else:
            self.codewriter.comment("***Skipping operation setarrayitem()***")


    def getarraysize(self, op):
        array, arraytype = self.db.repr_argwithtype(op.args[0])
        tmpvar = self.db.repr_tmpvar()
        self.codewriter.getelementptr(tmpvar, arraytype, array, ("uint", 0))
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        self.codewriter.load(targetvar, targettype, tmpvar)
