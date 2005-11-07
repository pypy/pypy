import py
from pypy.objspace.flow.model import Constant
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.rmodel import inputconst, getfunctionptr
from pypy.translator.js.extfuncnode import ExternalFuncNode
from pypy.translator.js.log import log 
log = log.opwriter

class OpWriter(object):
    binary_operations = {'int_mul': '*',
                         'int_add': '+',
                         'int_sub': '-',
                         'int_floordiv': '/',
                         'int_mod': '%',
                         'int_and': '&',
                         'int_or': '|',
                         'int_xor': '^',
                         'int_lshift': '<<',
                         'int_rshift': '>>',
                         'int_lt': '<',
                         'int_le': '<=',
                         'int_eq': '==',
                         'int_ne': '!=',
                         'int_ge': '>=',
                         'int_gt': '>',

                         'uint_mul': '*',
                         'uint_add': '+',
                         'uint_sub': '-',
                         'uint_floordiv': '/',
                         'uint_mod': '%',
                         'uint_and': '&',
                         'uint_or': '|',
                         'uint_xor': '^',
                         'uint_lshift': '<<',
                         'uint_rshift': '>>',
                         'uint_lt': '<',
                         'uint_le': '<=',
                         'uint_eq': '==',
                         'uint_ne': '!=',
                         'uint_ge': '>=',
                         'uint_gt': '>',

                         'unichar_lt': '<',
                         'unichar_le': '<=',
                         'unichar_eq': '==',
                         'unichar_ne': '!=',
                         'unichar_ge': '>=',
                         'unichar_gt': '>',

                         'float_mul': '*',
                         'float_add': '+',
                         'float_sub': '-',
                         'float_truediv': '/',
                         'float_mod': '%',
                         'float_lt': '<',
                         'float_le': '<=',
                         'float_eq': '==',
                         'float_ne': '!=',
                         'float_ge': '>=',
                         'float_gt': '>',

                         'ptr_eq': '==',
                         'ptr_ne': '!=',
                         }

    char_operations  = {'char_lt': '<',
                        'char_le': '<=',
                        'char_eq': '==',
                        'char_ne': '!=',
                        'char_ge': '>=',
                        'char_gt': '>'}

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
            elif op.opname in self.char_operations:
                self.char_binaryop(op)
            elif op.opname.startswith('cast_'):
                if op.opname == 'cast_char_to_int':
                    self.cast_char_to_int(op)
                else:
                    self.cast_primitive(op)
            else:
                meth = getattr(self, op.opname, None)
                if not meth:
                    raise Exception, "operation %s not found" % op.opname
                    return
                meth(op)    

    def _generic_pow(self, op, onestr): 
        mult_val = self.db.repr_arg(op.args[0])
        last_val = mult_val
        try:
            value = "NO VALUE"
            value = op.args[1].value
            operand = int(value)
        except Exception, exc:
            msg = 'XXX: Error: _generic_pow: Variable '\
                  '%s - failed to convert to int %s' % (value, str(exc))
            self.codewriter.comment(msg)
            return
        if operand < 1:
            res_val = onestr
        else:
            res_val = mult_val
            for ii in range(operand - 1):
                res_val = self.db.repr_tmpvar()
                self.codewriter.binaryop('*', 
                                         res_val,
                                         last_val,
                                         mult_val)
                last_val = res_val
        targetvar = self.db.repr_arg(op.result)
        self.codewriter.cast(targetvar, mult_type, res_val, mult_type)        
        
    def _skipped(self, op):
            #self.codewriter.comment('Skipping operation %s()' % op.opname)
            pass
    keepalive = _skipped 
    
    def int_abs(self, op):
        #ExternalFuncNode.used_external_functions[functionref] = True
        self.codewriter.call(self.db.repr_arg(op.result),
                             'Math.abs',
                             [self.db.repr_arg(op.args[0])])
    float_abs = int_abs

    def int_pow(self, op):
        self._generic_pow(op, "1") 
    uint_pow = int_pow
    
    def float_pow(self, op):
        self._generic_pow(op, "1.0") 

    def _generic_neg(self, op): 
        self.codewriter.neg(self.db.repr_arg(op.result),
                            self.db.repr_arg(op.args[0]))
    int_neg   = _generic_neg
    uint_neg  = _generic_neg
    float_neg = _generic_neg

    def bool_not(self, op):
        self.codewriter.binaryop('^',
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]), 
                                 "true")

    def int_invert(self, op):
        self.codewriter.binaryop('^',
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]), 
                                 -1)

    def uint_invert(self, op):
        self.codewriter.binaryop('^',
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]), 
                                 str((1L<<32) - 1))

    def binaryop(self, op):
        name = self.binary_operations[op.opname]
        assert len(op.args) == 2
        self.codewriter.binaryop(name,
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]),
                                 self.db.repr_arg(op.args[1]))

    def char_binaryop(self, op):
        name = self.char_operations[op.opname]
        assert len(op.args) == 2
        res = self.db.repr_arg(op.result)
        c1 = self.db.repr_tmpvar()
        c2 = self.db.repr_tmpvar()
        self.codewriter.cast(c1, "sbyte", self.db.repr_arg(op.args[0]), "ubyte")
        self.codewriter.cast(c2, "sbyte", self.db.repr_arg(op.args[1]), "ubyte")
        self.codewriter.binaryop(name, res, c1, c2)

    def cast_char_to_int(self, op):
        " works for all casts "
        assert len(op.args) == 1
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_arg_type(op.result)
        fromvar = self.db.repr_arg(op.args[0])
        fromtype = self.db.repr_arg_type(op.args[0])
        intermediate = self.db.repr_tmpvar()
        self.codewriter.cast(intermediate, fromtype, fromvar, "ubyte")
        self.codewriter.cast(targetvar, "ubyte", intermediate, targettype)

    def cast_primitive(self, op):
        " works for all casts "
        assert len(op.args) == 1
        targetvar = self.db.repr_arg(op.result)
        targettype = self.db.repr_concretetype(op.result.concretetype)
        fromvar = self.db.repr_arg(op.args[0])
        fromtype = self.db.repr_concretetype(op.args[0].concretetype)
        if op.opname not in ('cast_pointer',):
            self.codewriter.comment('next line=%s, from %s to %s' % (op.opname, fromtype, targettype))
        self.codewriter.cast(targetvar, fromtype, fromvar, targettype)
    same_as = cast_primitive

    def int_is_true(self, op):
        self.codewriter.binaryop("!=",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]),
                                 "0")
    uint_is_true = int_is_true

    def float_is_true(self, op):
        self.codewriter.binaryop("!=",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]),
                                 "0.0")

    def ptr_nonzero(self, op):
        self.codewriter.binaryop("!=",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]),
                                 "null")

    def ptr_iszero(self, op):
        self.codewriter.binaryop("==",
                                 self.db.repr_arg(op.result),
                                 self.db.repr_arg(op.args[0]),
                                 "null")

    def direct_call(self, op):
        op_args = [arg for arg in op.args
                   if arg.concretetype is not lltype.Void]
        assert len(op_args) >= 1
        targetvar = self.db.repr_arg(op.result)
        functionref = self.db.repr_arg(op_args[0])
        argrefs = self.db.repr_arg_multi(op_args[1:])
        if functionref == 'll_stack_check': #XXX what to do here?
            self.codewriter.comment('Skipping: %s = %s()' % (targetvar, functionref))
            return
        self.codewriter.call(targetvar, functionref, argrefs)

    def invoke(self, op):
        op_args = [arg for arg in op.args
                   if arg.concretetype is not lltype.Void]

        if op.opname == 'invoke:direct_call':
            functionref = self.db.repr_arg(op_args[0])
        else:   #operation
            opname = op.opname.split(':',1)[1]
            op_args = [opname] + op_args
            functionref = op_args[0]
            if functionref in extfunctions:
                ExternalFuncNode.used_external_functions[functionref] = True
            else:
                msg = "exception raising operation %s not found" %(op.opname,)
                self.codewriter.comment('XXX: Error: ' + msg)
                # XXX commented out for testing
                #assert functionref in extfunctions, msg

        assert len(op_args) >= 1
        # at least one label and one exception label
        assert len(self.block.exits) >= 2   

        link = self.block.exits[0]
        assert link.exitcase is None

        targetvar  = self.db.repr_arg(op.result)
        argrefs    = self.db.repr_arg_multi(op_args[1:])
        none_label = self.node.blockindex[link.target]
        no_exception = (none_label, link)

        exceptions = []
        for exit in self.block.exits[1:]:
            assert issubclass(exit.exitcase, Exception)
            exception_match  = self.db.translator.rtyper.getexceptiondata().ll_exception_match.__name__
            exception_ref    = self.db.obj2node[exit.llexitcase._obj].get_ref()
            exception_target = self.node.blockindex[exit.target]
            exception        = (exception_match, exception_ref, exception_target, exit)
            exceptions.append(exception)

        self.codewriter.call(targetvar, functionref, argrefs, no_exception, exceptions)

    def malloc(self, op): 
        arg_type = op.args[0].value
        targetvar = self.db.repr_arg(op.result) 
        type_ = self.db.repr_type(arg_type)
        self.codewriter.malloc(targetvar, type_)
    malloc_exception = malloc
    malloc_varsize = malloc

    def _getindexhelper(self, name, struct):
        assert name in list(struct._names)

        fieldnames = struct._names_without_voids()
        try:
            index = fieldnames.index(name)
        except ValueError:
            index = -1
        return index

    def getfield(self, op): 
        struct = self.db.repr_arg(op.args[0])
        targetvar = self.db.repr_arg(op.result)
        targettype = 'undefined' #self.db.repr_arg_type(op.result)
        if targettype != "void" and \
            not targetvar.startswith('etype_'):
            self.codewriter.append('%s = %s.%s' % (targetvar, struct, op.args[1].value)) #XXX move to codewriter
        else:
            self._skipped(op)
 
    def getsubstruct(self, op): 
        struct = self.db.repr_arg(op.args[0])
        #index = self._getindexhelper(op.args[1].value, op.args[0].concretetype.TO)
        targetvar = self.db.repr_arg(op.result)
        #targettype = self.db.repr_arg_type(op.result)
        #assert targettype != "void"
        self.codewriter.append('%s = %s.%s' % (targetvar, struct, op.args[1].value)) #XXX move to codewriter
        #self.codewriter.getelementptr(targetvar, structtype, struct, ("uint", index))        
         
    def setfield(self, op): 
        struct   = self.db.repr_arg(op.args[0])
        valuevar = self.db.repr_arg(op.args[2])
        valuetype = 'undefined'  #XXX how to get to this when no longer keep track of type
        if valuetype != "void":
            self.codewriter.append('%s.%s = %s' % (struct, op.args[1].value, valuevar)) #XXX move to codewriter
        else:
            self._skipped(op)

    def getarrayitem(self, op):        
        array = self.db.repr_arg(op.args[0])
        index = self.db.repr_arg(op.args[1])
        #indextype = self.db.repr_arg_type(op.args[1])
        targetvar = self.db.repr_arg(op.result)
        targettype = 'undefined' #self.db.repr_arg_type(op.result)
        if targettype != "void":
            #tmpvar = self.db.repr_tmpvar()
            #self.codewriter.getelementptr(tmpvar, arraytype, array,
            #                              ("uint", 1), (indextype, index))
            #self.codewriter.load(targetvar, targettype, tmpvar)
            self.codewriter.load(targetvar, array, (index,))
        else:
            self._skipped(op)

    def getarraysubstruct(self, op):        
        array = self.db.repr_arg(op.args[0])
        arraytype = ''
        index = self.db.repr_arg(op.args[1])
        indextype = '' #self.db.repr_arg_type(op.args[1])
        targetvar = self.db.repr_arg(op.result)
        self.codewriter.getelementptr(targetvar, arraytype, array,
                                      ("uint", 1), (indextype, index))

    def setarrayitem(self, op):
        array = self.db.repr_arg(op.args[0])
        index = self.db.repr_arg(op.args[1])
        #indextype = self.db.repr_arg_type(op.args[1])
        valuevar = self.db.repr_arg(op.args[2]) 
        valuetype = 'undefined' #self.db.repr_arg_type(op.args[2])
        if valuetype != "void":
            #tmpvar = self.db.repr_tmpvar()
            #self.codewriter.getelementptr(tmpvar, arraytype, array,
            #                          ("uint", 1), (indextype, index))
            #self.codewriter.store(valuetype, valuevar, tmpvar) 
            self.codewriter.store(array, (index,), valuevar)
        else:
            self._skipped(op)

    def getarraysize(self, op):
        array = self.db.repr_arg(op.args[0])
        #tmpvar = self.db.repr_tmpvar()
        #self.codewriter.getelementptr(tmpvar, arraytype, array, ("uint", 0))
        targetvar = self.db.repr_arg(op.result)
        #targettype = self.db.repr_arg_type(op.result)
        #self.codewriter.load(targetvar, targettype, tmpvar)
        self.codewriter.append('%s = %s.length' % (targetvar, array)) #XXX move to codewriter
