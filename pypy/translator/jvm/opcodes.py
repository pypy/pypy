"""

Mapping from OOType opcodes to JVM MicroInstructions.  Most of these
come from the oosupport directory.

"""

from pypy.translator.oosupport.metavm import \
     PushArg, PushAllArgs, StoreResult, InstructionList, New, OONewArray, DoNothing, Call,\
     SetField, GetField, DownCast, RuntimeNew, OOString, OOUnicode, \
     CastTo, PushPrimitive
from pypy.translator.jvm.metavm import \
     IndirectCall, JvmCallMethod, NewCustomDict, \
     CastPrimitive, PushPyPy, PushComparisonResult
from pypy.rpython.ootypesystem import ootype
from pypy.translator.jvm.cmpopcodes import cmp_opname

import pypy.translator.jvm.typesystem as jvm

def _proc(val):
    if isinstance(val, list):
        # Lists of instructions we leave alone:
        return InstructionList(val)
    elif isinstance(val, jvm.Method) and not val.is_static():
        # For virtual methods, we first push an instance of the relevant
        # class, then the arguments, and then invoke the method.  Note
        # that we only allow virtual methods of certain pre-designated
        # classes to be in the table.
        if val.class_name == jvm.jPyPy.name:
            return InstructionList(
                (PushPyPy, PushAllArgs, val, StoreResult))
        else:
            raise Exception("Unknown class for non-static method")
    # For anything else (static methods, strings, etc) we first push
    # all arguments, then invoke the emit() routine, and finally
    # store the result.
    return InstructionList((PushAllArgs, val, StoreResult))
        
def _proc_dict(original):
    
    """ Function which is used to post-process each entry in the
    opcodes table.  It also adds the entries for comparison operations
    from the cmpopcodes module. """

    res = {}
    
    for opname, val in original.items():
        res[opname] = _proc(val)

    for opname in cmp_opname.keys():
        res[opname] = _proc(PushComparisonResult)
        
    return res

def _check_zer(op):
    # Note: we convert from Java's ArithmeticException to RPython's
    # ZeroDivisionError in the *catch* code, not here where the
    # exception is generated.  See introduce_exception_conversions()
    # in node.py for details.
    return op

def _check_ovf(op):
    return op

Ignore = []
    

# This table maps the opcodes to micro-ops for processing them.
# It is post-processed by _proc.
opcodes = _proc_dict({
    # __________ object oriented operations __________
    'new':                      [New, StoreResult],
    'oonewarray':               [OONewArray, StoreResult],
    'runtimenew':               [RuntimeNew, StoreResult],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField, StoreResult],
    'oosend':                   [JvmCallMethod, StoreResult],
    'ooupcast':                 DoNothing,
    'oodowncast':               [DownCast, StoreResult],
    'cast_to_object':           DoNothing,
    'cast_from_object':         [DownCast, StoreResult],
    'instanceof':               [CastTo, StoreResult],
    'subclassof':               [PushAllArgs, jvm.SWAP, jvm.CLASSISASSIGNABLEFROM, StoreResult],
    'classof':                  [PushAllArgs, jvm.OBJECTGETCLASS, StoreResult],
    'gc_id':                    [PushAllArgs, jvm.SYSTEMIDENTITYHASH, StoreResult],   # XXX not implemented
    'gc_identityhash':          [PushAllArgs, jvm.SYSTEMIDENTITYHASH, StoreResult], 
    'oostring':                 [OOString, StoreResult],
    'oounicode':                [OOUnicode, StoreResult],
    'ooparse_float':            jvm.PYPYOOPARSEFLOAT,
    'oonewcustomdict':          [NewCustomDict, StoreResult],
    'same_as':                  DoNothing,
    'hint':                     [PushArg(0), StoreResult],
    'direct_call':              [Call, StoreResult],
    'indirect_call':            [PushAllArgs, IndirectCall, StoreResult],

    'gc__collect':              jvm.SYSTEMGC,
    'gc_set_max_heap_size':     Ignore,
    'resume_point':             Ignore,
    'jit_marker':               Ignore,
    'jit_force_virtualizable':  Ignore,
    'jit_force_virtual':        DoNothing,

    'debug_assert':              [], # TODO: implement?
    'debug_start_traceback':    Ignore,
    'debug_record_traceback':   Ignore,
    'debug_catch_exception':    Ignore,
    'debug_reraise_traceback':  Ignore,
    'debug_print_traceback':    Ignore,

    # __________ numeric operations __________

    'bool_not':                 'logical_not',

    'int_neg':                  jvm.INEG,
    'int_neg_ovf':              jvm.INEGOVF,
    'int_abs':                  'iabs',
    'int_abs_ovf':              jvm.IABSOVF,
    'int_invert':               'bitwise_negate',

    'int_add':                  jvm.IADD,
    'int_sub':                  jvm.ISUB,
    'int_mul':                  jvm.IMUL,
    'int_floordiv':             jvm.IDIV,
    'int_floordiv_zer':         _check_zer(jvm.IDIV),
    'int_mod':                  jvm.IREM,
    'int_and':                  jvm.IAND,
    'int_or':                   jvm.IOR,
    'int_lshift':               jvm.ISHL,
    'int_rshift':               jvm.ISHR,
    'int_xor':                  jvm.IXOR,
    'int_add_ovf':              jvm.IADDOVF,
    'int_add_nonneg_ovf':       jvm.IADDOVF,
    'int_sub_ovf':              jvm.ISUBOVF,
    'int_mul_ovf':              jvm.IMULOVF,
    'int_floordiv_ovf':         jvm.IFLOORDIVOVF,
    'int_mod_zer':              _check_zer(jvm.IREM),
    'int_mod_ovf':              jvm.IREMOVF,
    'int_and_ovf':              jvm.IAND,
    'int_or_ovf':               jvm.IOR,

    'int_lshift_ovf':           jvm.ISHLOVF,

    'int_rshift_ovf':           jvm.ISHR, # these can't overflow!
    'int_xor_ovf':              jvm.IXOR,
    'int_floordiv_ovf_zer':     jvm.IFLOORDIVZEROVF,
    'int_mod_ovf_zer':          _check_zer(jvm.IREMOVF),

    'uint_invert':              'bitwise_negate',

    'uint_add':                 jvm.IADD,
    'uint_sub':                 jvm.ISUB,
    'uint_mul':                 jvm.PYPYUINTMUL,
    'uint_div':                 jvm.PYPYUINTDIV,
    'uint_truediv':             None,    # TODO
    'uint_floordiv':            jvm.PYPYUINTDIV,
    'uint_mod':                 jvm.PYPYUINTMOD,
    'uint_and':                 jvm.IAND,
    'uint_or':                  jvm.IOR,
    'uint_lshift':              jvm.ISHL,
    'uint_rshift':              jvm.IUSHR,
    'uint_xor':                 jvm.IXOR,

    'float_neg':                jvm.DNEG,
    'float_abs':                'dbl_abs',

    'float_add':                jvm.DADD,
    'float_sub':                jvm.DSUB,
    'float_mul':                jvm.DMUL,
    'float_truediv':            jvm.DDIV,

    'llong_neg':                jvm.LNEG,
    'llong_neg_ovf':            jvm.LNEGOVF,
    'llong_abs':                jvm.MATHLABS,
    'llong_abs_ovf':            jvm.LABSOVF,
    'llong_invert':             jvm.PYPYLONGBITWISENEGATE,

    'llong_add':                jvm.LADD,
    'llong_sub':                jvm.LSUB,
    'llong_mul':                jvm.LMUL,
    'llong_div':                jvm.LDIV,
    'llong_truediv':            None, # TODO
    'llong_floordiv':           jvm.LDIV,
    'llong_floordiv_zer':       _check_zer(jvm.LDIV),
    'llong_mod':                jvm.LREM,
    'llong_mod_zer':            _check_zer(jvm.LREM),
    'llong_and':                jvm.LAND,
    'llong_or':                 jvm.LOR,
    'llong_lshift':             [PushAllArgs, jvm.L2I, jvm.LSHL, StoreResult],
    'llong_rshift':             [PushAllArgs, jvm.L2I, jvm.LSHR, StoreResult],
    'llong_xor':                jvm.LXOR,
    'llong_floordiv_ovf':       jvm.LFLOORDIVOVF,
    'llong_floordiv_ovf_zer':   jvm.LFLOORDIVZEROVF,    
    'llong_mod_ovf':            jvm.LREMOVF,
    'llong_lshift_ovf':         jvm.LSHLOVF,

    'ullong_invert':            jvm.PYPYLONGBITWISENEGATE,

    'ullong_add':               jvm.LADD,
    'ullong_sub':               jvm.LSUB,
    'ullong_mul':               jvm.LMUL,
    'ullong_div':               jvm.LDIV, # valid?
    'ullong_truediv':           None, # TODO
    'ullong_floordiv':          jvm.LDIV, # valid?
    'ullong_mod':               jvm.PYPYULONGMOD,
    'ullong_lshift':            [PushAllArgs, jvm.L2I, jvm.LSHL, StoreResult],
    'ullong_rshift':            [PushAllArgs, jvm.L2I, jvm.LUSHR, StoreResult],
    'ullong_mod_zer':           jvm.PYPYULONGMOD,

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick. #THIS COMMENT NEEDS TO BE VALIDATED AND UPDATED
    'cast_bool_to_int':         DoNothing,
    'cast_bool_to_uint':        DoNothing,
    'cast_bool_to_float':       jvm.PYPYBOOLTODOUBLE, #PAUL, inefficient    
    'cast_char_to_int':         DoNothing,
    'cast_unichar_to_int':      DoNothing,
    'cast_int_to_char':         DoNothing,
    'cast_int_to_unichar':      DoNothing,
    'cast_int_to_uint':         DoNothing,
    'cast_int_to_float':        jvm.I2D,
    'cast_int_to_longlong':     jvm.I2L,
    'cast_uint_to_int':         DoNothing,
    'cast_uint_to_float':       jvm.PYPYUINTTODOUBLE, 
    'cast_float_to_int':        jvm.D2I,
    'cast_float_to_longlong':   jvm.PYPYDOUBLETOLONG, #PAUL
    'cast_float_to_uint':       jvm.PYPYDOUBLETOUINT,
    'truncate_longlong_to_int': jvm.L2I,
    'cast_longlong_to_float':   jvm.L2D,
    'cast_primitive':           [PushAllArgs, CastPrimitive, StoreResult],
})
