"""

Mapping from OOType opcodes to JVM MicroInstructions.  Most of these
come from the oosupport directory.

"""

from pypy.translator.cli.metavm import  Call, CallMethod, RuntimeNew, \
     IndirectCall, GetField, SetField, CastTo, OOString, DownCast, NewCustomDict,\
     CastWeakAdrToPtr, MapException
from pypy.translator.oosupport.metavm import PushArg, PushAllArgs, StoreResult, InstructionList,\
    New
from pypy.translator.cli.cts import WEAKREF

opcodes = {
    # __________ object oriented operations __________
    'new':                      [New],
    'runtimenew':               [RuntimeNew],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField],
    'oosend':                   [CallMethod],
    'ooupcast':                 DoNothing,
    'oodowncast':               [DownCast],
    'oois':                     'ceq',
    'oononnull':                [PushAllArgs, 'ldnull', 'ceq']+Not,
    'instanceof':               [CastTo, 'ldnull', 'cgt.un'],
    'subclassof':               [PushAllArgs, 'call bool [pypylib]pypy.runtime.Utils::SubclassOf(class [mscorlib]System.Type, class[mscorlib]System.Type)'],
    'ooidentityhash':           [PushAllArgs, 'callvirt instance int32 object::GetHashCode()'],
    'oohash':                   [PushAllArgs, 'callvirt instance int32 object::GetHashCode()'],    
    'oostring':                 [OOString],
    'ooparse_int':              [PushAllArgs, 'call int32 [pypylib]pypy.runtime.Utils::OOParseInt(string, int32)'],
    'oonewcustomdict':          [NewCustomDict],
    
    'same_as':                  DoNothing,
    'hint':                     [PushArg(0), StoreResult],
    'direct_call':              [Call],
    'indirect_call':            [IndirectCall],

    'cast_ptr_to_weakadr':      [PushAllArgs, 'newobj instance void class %s::.ctor(object)' % WEAKREF],
    'cast_weakadr_to_ptr':      [CastWeakAdrToPtr],
    'gc__collect':              'call void class [mscorlib]System.GC::Collect()',
    'resume_point':             Ignore,

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
    'int_neg':                  'INEG',
    'int_neg_ovf':              None, # How to handle overflow?
    'int_abs':                  'iabs',
    'int_abs_ovf':              _check_ovf('iabs'),
    'int_invert':               'bitwise_negate',

    'int_add':                  'IADD',
    'int_sub':                  'ISUB',
    'int_mul':                  'IMUL',
    'int_floordiv':             'IDIV',
    'int_floordiv_zer':         _check_zer('IDIV'),
    'int_mod':                  'IREM',
    'int_lt':                   'less_than',
    'int_le':                   'less_equals',
    'int_eq':                   'equals',
    'int_ne':                   'not_equals',
    'int_gt':                   'greater_than',
    'int_ge':                   'greater_equals',
    'int_and':                  'IAND',
    'int_or':                   'IOR',
    'int_lshift':               'ISHL',
    'int_rshift':               'ISHR',
    'int_xor':                  'IXOR',
    'int_add_ovf':              _check_ovf('IADD'),
    'int_sub_ovf':              _check_ovf('ISUB'),
    'int_mul_ovf':              _check_ovf('IMUL'),
    'int_floordiv_ovf':         'IDIV', # these can't overflow!
    'int_mod_ovf':              'IREM',
    'int_lt_ovf':               'less_than',
    'int_le_ovf':               'less_equals',
    'int_eq_ovf':               'equals',
    'int_ne_ovf':               'not_equals',
    'int_gt_ovf':               'greater_than',
    'int_ge_ovf':               'greater_equals',
    'int_and_ovf':              'IAND',
    'int_or_ovf':               'IOR',

    'int_lshift_ovf':           _check_ovf('ISHL'),
    'int_lshift_ovf_val':       _check_ovf('ISHL'), # VAL??

    'int_rshift_ovf':           'ISHR', # these can't overflow!
    'int_xor_ovf':              'IXOR',
    'int_floordiv_ovf_zer':     _check_zer('IDIV'),
    'int_mod_ovf_zer':          _check_zer('IREM'),

    'uint_is_true':             'not_equals_zero',
    'uint_invert':              'bitwise_negate',

    'uint_add':                 'IADD',
    'uint_sub':                 'ISUB',
    'uint_mul':                 'IMUL',
    'uint_div':                 'IDIV',  # valid?
    'uint_truediv':             None,    # TODO
    'uint_floordiv':            'IDIV',  # valid?
    'uint_mod':                 'IREM',  # valid?
    'uint_lt':                  'u_less_than',
    'uint_le':                  'u_less_equals',
    'uint_eq':                  'u_equals',
    'uint_ne':                  'u_not_equals',
    'uint_gt':                  'u_greater_than',
    'uint_ge':                  'u_greater_equals',
    'uint_and':                 'IAND',
    'uint_or':                  'IOR',
    'uint_lshift':              'ISHL',
    'uint_rshift':              'IUSHR',
    'uint_xor':                 'IXOR',

    'float_is_true':            [PushAllArgs, 'DCONST_0', 'dbl_not_equals'],
    'float_neg':                'DNEG',
    'float_abs':                'dbl_abs',

    'float_add':                'DADD',
    'float_sub':                'DSUB',
    'float_mul':                'DMUL',
    'float_truediv':            'DDIV', 
    'float_mod':                'DREM', # use Math.IEEEremainder?
    'float_lt':                 'dbl_less_than',     
    'float_le':                 'dbl_less_equals',   
    'float_eq':                 'dbl_equals',        
    'float_ne':                 'dbl_not_equals',    
    'float_gt':                 'dbl_greater_than',  
    'float_ge':                 'dbl_greater_equals',
    'float_floor':              'MATHFLOOR',
    'float_fmod':               'DREM', # DREM is akin to fmod() in C

    'llong_is_true':            [PushAllArgs, 'LCONST_0', 'long_not_equals'],
    'llong_neg':                'LNEG',
    'llong_neg_ovf':            _check_ovf('LNEG'),
    'llong_abs':                'MATHLABS',
    'llong_invert':             'PYPYLONGBITWISENEGATE',

    'llong_add':                'LADD',
    'llong_sub':                'LSUB',
    'llong_mul':                'LMUL',
    'llong_div':                'LDIV',
    'llong_truediv':            None, # TODO
    'llong_floordiv':           'LDIV',
    'llong_mod':                'LREM',
    'llong_lt':                 'long_less_than',     
    'llong_le':                 'long_less_equals',   
    'llong_eq':                 'long_equals',        
    'llong_ne':                 'long_not_equals',    
    'llong_gt':                 'long_greater_than',  
    'llong_ge':                 'long_greater_equals',
    'llong_and':                'LAND',
    'llong_or':                 'LOR',
    'llong_lshift':             'LSHL',
    'llong_rshift':             'LSHR',
    'llong_xor':                'LXOR',

    'ullong_is_true':           [PushAllArgs, 'LCONST_0', 'long_not_equals'],
    'ullong_invert':            'PYPYLONGBITWISENEGATE',

    'ullong_add':               'LADD',
    'ullong_sub':               'LSUB',
    'ullong_mul':               'LMUL',
    'ullong_div':               'LDIV', # valid?
    'ullong_truediv':           None, # TODO
    'ullong_floordiv':          'LDIV', # valid?
    'ullong_mod':               'LREM', # valid?
    'ullong_lt':                'ulong_less_than',     
    'ullong_le':                'ulong_less_equals',   
    'ullong_eq':                'ulong_equals',        
    'ullong_ne':                'ulong_not_equals',    
    'ullong_gt':                'ulong_greater_than',  
    'ullong_ge':                'ulong_greater_equals',

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         DoNothing,
    'cast_bool_to_uint':        DoNothing,
    'cast_bool_to_float':       [PushAllArgs, 'not_equals_zero', 'I2D'],
    
    'cast_char_to_int':         DoNothing,
    'cast_unichar_to_int':      DoNothing,
    'cast_int_to_char':         DoNothing,
    'cast_int_to_unichar':      DoNothing,
    'cast_int_to_uint':         DoNothing,
    'cast_int_to_float':        'I2D',
    'cast_int_to_longlong':     'I2L',
    'cast_uint_to_int':         DoNothing,
    'cast_uint_to_float':       PYPYUINTTODOUBLE, 
    'cast_float_to_int':        'D2I',
    'cast_float_to_uint':       PYPYDOUBLETOUINT,
    'truncate_longlong_to_int': 'L2I',
    
}
