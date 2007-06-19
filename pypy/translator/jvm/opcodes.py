"""

Mapping from OOType opcodes to JVM MicroInstructions.  Most of these
come from the oosupport directory.

"""

from pypy.translator.oosupport.metavm import \
     PushArg, PushAllArgs, StoreResult, InstructionList, New, DoNothing, Call,\
     SetField, GetField, DownCast, RuntimeNew, OOString, CastTo
from pypy.translator.jvm.metavm import \
     IndirectCall, JvmCallMethod, TranslateException, NewCustomDict, \
     CastPtrToWeakAddress, CastWeakAddressToPtr

import pypy.translator.jvm.generator as jvmgen
import pypy.translator.jvm.typesystem as jvmtype

def _proc(val):
    """ Function which is used to post-process each entry in the
    opcodes table; it adds a PushAllArgs and StoreResult by default,
    unless the entry is a list already. """
    if not isinstance(val, list):
        val = InstructionList((PushAllArgs, val, StoreResult))
    else:
        val = InstructionList(val)
    return val

def _check_zer(op):
    return [TranslateException(
        jvmtype.jArithmeticException,
        'throwZeroDivisionError',
        _proc(op))]

def _check_ovf(op):
    # TODO
    return op
    
def _check_unary_ovf(op):
    # TODO  We should just use rlib's overflow dtection
    # Assume LLONG_MIN = (- LLONG_MAX-1)
#    if op.operand == LLONG_MIN:
#        return [TranslateException(
#            jvmtype.jArithmeticException,
#            'throwOverflowError',
#            _proc(op))]
#    else:
#        return op
    return op

# This table maps the opcodes to micro-ops for processing them.
# It is post-processed by _proc.
_opcodes = {
    # __________ object oriented operations __________
    'new':                      [New, StoreResult],
    'runtimenew':               [RuntimeNew, StoreResult],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField, StoreResult],
    'oosend':                   [JvmCallMethod, StoreResult],
    'ooupcast':                 DoNothing,
    'oodowncast':               [DownCast, StoreResult],
    'oois':                     'ref_is_eq',
    'oononnull':                'is_not_null',
    'instanceof':               [CastTo, StoreResult],
    'subclassof':               [PushAllArgs, jvmgen.SWAP, jvmgen.CLASSISASSIGNABLEFROM, StoreResult],
    'ooidentityhash':           [PushAllArgs, jvmgen.OBJHASHCODE, StoreResult], 
    'oohash':                   [PushAllArgs, jvmgen.OBJHASHCODE, StoreResult], 
    'oostring':                 [OOString, StoreResult],
    #'ooparse_int':              [PushAllArgs, 'call int32 [pypylib]pypy.runtime.Utils::OOParseInt(string, int32)'],
    'oonewcustomdict':          [NewCustomDict, StoreResult],
    #
    'same_as':                  DoNothing,
    'hint':                     [PushArg(0), StoreResult],
    'direct_call':              [Call, StoreResult],
    'indirect_call':            [PushAllArgs, IndirectCall, StoreResult],

    'cast_ptr_to_weakadr':      [CastPtrToWeakAddress],
    'cast_weakadr_to_ptr':      CastWeakAddressToPtr,
    #'gc__collect':              'call void class [mscorlib]System.GC::Collect()',
    #'resume_point':             Ignore,

    'debug_assert':              [], # TODO: implement?

    # __________ numeric operations __________

    'bool_not':                 'logical_not',

    'char_lt':                  'less_than',
    'char_le':                  'less_equals',
    'char_eq':                  'equals',
    'char_ne':                  'not_equals',
    'char_gt':                  'greater_than',
    'char_ge':                  'greater_equals',

    'unichar_eq':               'equals',
    'unichar_ne':               'not_equals',

    'int_is_true':              'not_equals_zero',
    'int_neg':                  jvmgen.INEG,
    'int_neg_ovf':              None, # How to handle overflow?
    'int_abs':                  'iabs',
    'int_abs_ovf':              _check_ovf('iabs'),
    'int_invert':               'bitwise_negate',

    'int_add':                  jvmgen.IADD,
    'int_sub':                  jvmgen.ISUB,
    'int_mul':                  jvmgen.IMUL,
    'int_floordiv':             jvmgen.IDIV,
    'int_floordiv_zer':         _check_zer(jvmgen.IDIV),
    'int_mod':                  jvmgen.IREM,
    'int_lt':                   'less_than',
    'int_le':                   'less_equals',
    'int_eq':                   'equals',
    'int_ne':                   'not_equals',
    'int_gt':                   'greater_than',
    'int_ge':                   'greater_equals',
    'int_and':                  jvmgen.IAND,
    'int_or':                   jvmgen.IOR,
    'int_lshift':               jvmgen.ISHL,
    'int_rshift':               jvmgen.ISHR,
    'int_xor':                  jvmgen.IXOR,
    'int_add_ovf':              _check_ovf(jvmgen.IADD),
    'int_sub_ovf':              _check_ovf(jvmgen.ISUB),
    'int_mul_ovf':              _check_ovf(jvmgen.IMUL),
    'int_floordiv_ovf':         jvmgen.IDIV, # these can't overflow!
    'int_mod_ovf':              jvmgen.IREM,
    'int_lt_ovf':               'less_than',
    'int_le_ovf':               'less_equals',
    'int_eq_ovf':               'equals',
    'int_ne_ovf':               'not_equals',
    'int_gt_ovf':               'greater_than',
    'int_ge_ovf':               'greater_equals',
    'int_and_ovf':              jvmgen.IAND,
    'int_or_ovf':               jvmgen.IOR,

    'int_lshift_ovf':           _check_ovf(jvmgen.ISHL),
    'int_lshift_ovf_val':       _check_ovf(jvmgen.ISHL), # VAL??

    'int_rshift_ovf':           jvmgen.ISHR, # these can't overflow!
    'int_xor_ovf':              jvmgen.IXOR,
    'int_floordiv_ovf_zer':     _check_zer(jvmgen.IDIV),
    'int_mod_ovf_zer':          _check_zer(jvmgen.IREM),

    'uint_is_true':             'not_equals_zero',
    'uint_invert':              'bitwise_negate',

    'uint_add':                 jvmgen.IADD,
    'uint_sub':                 jvmgen.ISUB,
    'uint_mul':                 jvmgen.IMUL,
    'uint_div':                 jvmgen.IDIV,  # valid?
    'uint_truediv':             None,    # TODO
    'uint_floordiv':            jvmgen.IDIV,  # valid?
    'uint_mod':                 jvmgen.IREM,  # valid?
    'uint_lt':                  'u_less_than',
    'uint_le':                  'u_less_equals',
    'uint_eq':                  'u_equals',
    'uint_ne':                  'u_not_equals',
    'uint_gt':                  'u_greater_than',
    'uint_ge':                  'u_greater_equals',
    'uint_and':                 jvmgen.IAND,
    'uint_or':                  jvmgen.IOR,
    'uint_lshift':              jvmgen.ISHL,
    'uint_rshift':              jvmgen.IUSHR,
    'uint_xor':                 jvmgen.IXOR,

    'float_is_true':            [PushAllArgs,
                                 jvmgen.DCONST_0,
                                 'dbl_not_equals'],
    'float_neg':                jvmgen.DNEG,
    'float_abs':                'dbl_abs',

    'float_add':                jvmgen.DADD,
    'float_sub':                jvmgen.DSUB,
    'float_mul':                jvmgen.DMUL,
    'float_truediv':            jvmgen.DDIV, 
    'float_lt':                 'dbl_less_than',     
    'float_le':                 'dbl_less_equals',   
    'float_eq':                 'dbl_equals',        
    'float_ne':                 'dbl_not_equals',    
    'float_gt':                 'dbl_greater_than',  
    'float_ge':                 'dbl_greater_equals',

    'llong_is_true':            [PushAllArgs,
                                 jvmgen.LCONST_0,
                                 'long_not_equals'],
    'llong_neg':                jvmgen.LNEG,
    'llong_neg_ovf':            _check_ovf(jvmgen.LNEG),
    'llong_abs':                jvmgen.MATHLABS,
    'llong_invert':             jvmgen.PYPYLONGBITWISENEGATE,

    'llong_add':                jvmgen.LADD,
    'llong_sub':                jvmgen.LSUB,
    'llong_mul':                jvmgen.LMUL,
    'llong_div':                jvmgen.LDIV,
    'llong_truediv':            None, # TODO
    'llong_floordiv':           jvmgen.LDIV,
    'llong_mod':                jvmgen.LREM,
    'llong_lt':                 'long_less_than',     
    'llong_le':                 'long_less_equals',   
    'llong_eq':                 'long_equals',        
    'llong_ne':                 'long_not_equals',    
    'llong_gt':                 'long_greater_than',  
    'llong_ge':                 'long_greater_equals',
    'llong_and':                jvmgen.LAND,
    'llong_or':                 jvmgen.LOR,
    'llong_lshift':             jvmgen.LSHL,
    'llong_rshift':             jvmgen.LSHR,
    'llong_xor':                jvmgen.LXOR,

    'ullong_is_true':           [PushAllArgs,
                                 jvmgen.LCONST_0,
                                 'long_not_equals'],
    'ullong_invert':            jvmgen.PYPYLONGBITWISENEGATE,

    'ullong_add':               jvmgen.LADD,
    'ullong_sub':               jvmgen.LSUB,
    'ullong_mul':               jvmgen.LMUL,
    'ullong_div':               jvmgen.LDIV, # valid?
    'ullong_truediv':           None, # TODO
    'ullong_floordiv':          jvmgen.LDIV, # valid?
    'ullong_mod':               jvmgen.LREM, # valid?
    'ullong_lt':                'ulong_less_than',     
    'ullong_le':                'ulong_less_equals',   
    'ullong_eq':                'ulong_equals',        
    'ullong_ne':                'ulong_not_equals',    
    'ullong_gt':                'ulong_greater_than',  
    'ullong_ge':                'ulong_greater_equals',

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick. #THIS COMMENT NEEDS TO BE VALIDATED AND UPDATED
    'cast_bool_to_int':         DoNothing,
    'cast_bool_to_uint':        DoNothing,
    'cast_bool_to_float':       [PushAllArgs, 'not_equals_zero', jvmgen.I2D],
    
    'cast_char_to_int':         DoNothing,
    'cast_unichar_to_int':      DoNothing,
    'cast_int_to_char':         DoNothing,
    'cast_int_to_unichar':      DoNothing,
    'cast_int_to_uint':         DoNothing,
    'cast_int_to_float':        jvmgen.I2D,
    'cast_int_to_longlong':     jvmgen.I2L,
    'cast_uint_to_int':         DoNothing,
    'cast_uint_to_float':       jvmgen.PYPYUINTTODOUBLE, 
    'cast_float_to_int':        jvmgen.D2I,
    #'cast_float_to_longlong':   jvmgen.D2L, #PAUL
    #'cast_float_to_longlong':   jvmgen.PYPYDOUBLETOLONG, #PAUL
    'cast_float_to_uint':       jvmgen.PYPYDOUBLETOUINT,
    'truncate_longlong_to_int': jvmgen.L2I,
    'cast_longlong_to_float':   jvmgen.L2D,
    
}

opcodes = {}
for opc, val in _opcodes.items():
    opcodes[opc] = _proc(val)
del _opcodes
