DoNothing = object()
PushArgs = object()

# come useful instruction patterns
Not = ['ldc.i4.0', 'ceq']

def _not(op):
    return [PushArgs, op]+Not


opcodes = {
    'same_as':                  DoNothing, # TODO: does same_as really do nothing else than renaming?    
    'direct_call':              None, # for now it's a special case
    'indirect_call':            None,

    # __________ numeric operations __________

    'bool_not':                 Not,

    'char_lt':                  'clt',
    'char_le':                  None,
    'char_eq':                  'ceq',
    'char_ne':                  None,
    'char_gt':                  None,
    'char_ge':                  None,

    'unichar_eq':               None,
    'unichar_ne':               None,

    'int_is_true':              DoNothing,
    'int_neg':                  'neg',
    'int_neg_ovf':              ['ldc.i4.0', PushArgs, 'sub.ovf'],
    'int_abs':                  None, # TODO
    'int_abs_ovf':              None, # TODO
    'int_invert':               'not',

    'int_add':                  'add',
    'int_sub':                  'sub',
    'int_mul':                  'mul',
    'int_div':                  'div',
    'int_truediv':              None, # TODO
    'int_floordiv':             'div',
    'int_mod':                  'rem',
    'int_lt':                   'clt',
    'int_le':                   _not('cgt'),
    'int_eq':                   'ceq',
    'int_ne':                   _not('ceq'),
    'int_gt':                   'cgt',
    'int_ge':                   _not('clt'),
    'int_and':                  'and',
    'int_or':                   'or',
    'int_lshift':               'shl',
    'int_rshift':               'shr',
    'int_xor':                  'xor',
    'int_add_ovf':              None,
    'int_sub_ovf':              None,
    'int_mul_ovf':              None,
    'int_div_ovf':              None,
    'int_truediv_ovf':          None,
    'int_floordiv_ovf':         None,
    'int_mod_ovf':              None,
    'int_lt_ovf':               None,
    'int_le_ovf':               None,
    'int_eq_ovf':               None,
    'int_ne_ovf':               None,
    'int_gt_ovf':               None,
    'int_ge_ovf':               None,
    'int_and_ovf':              None,
    'int_or_ovf':               None,
    'int_lshift_ovf':           None,
    'int_rshift_ovf':           None,
    'int_xor_ovf':              None,
    'int_floordiv_ovf_zer':     None,
    'int_mod_ovf_zer':          None,

    'uint_is_true':             None,
    'uint_neg':                 None,
    'uint_abs':                 None,
    'uint_invert':              None,

    'uint_add':                 None,
    'uint_sub':                 None,
    'uint_mul':                 None,
    'uint_div':                 None,
    'uint_truediv':             None,
    'uint_floordiv':            None,
    'uint_mod':                 None,
    'uint_lt':                  None,
    'uint_le':                  None,
    'uint_eq':                  None,
    'uint_ne':                  None,
    'uint_gt':                  None,
    'uint_ge':                  None,
    'uint_and':                 None,
    'uint_or':                  None,
    'uint_lshift':              None,
    'uint_rshift':              None,
    'uint_xor':                 None,

    'float_is_true':            None,
    'float_neg':                None,
    'float_abs':                None,

    'float_add':                None,
    'float_sub':                None,
    'float_mul':                None,
    'float_div':                None,
    'float_truediv':            None,
    'float_floordiv':           None,
    'float_mod':                None,
    'float_lt':                 None,
    'float_le':                 None,
    'float_eq':                 None,
    'float_ne':                 None,
    'float_gt':                 None,
    'float_ge':                 None,
    'float_floor':              None,
    'float_fmod':               None,

    'llong_is_true':            None,
    'llong_neg':                None,
    'llong_abs':                None,
    'llong_invert':             None,

    'llong_add':                None,
    'llong_sub':                None,
    'llong_mul':                None,
    'llong_div':                None,
    'llong_truediv':            None,
    'llong_floordiv':           None,
    'llong_mod':                None,
    'llong_lt':                 None,
    'llong_le':                 None,
    'llong_eq':                 None,
    'llong_ne':                 None,
    'llong_gt':                 None,
    'llong_ge':                 None,

    'ullong_is_true':           None,
    'ullong_neg':               None,
    'ullong_abs':               None,
    'ullong_invert':            None,

    'ullong_add':               None,
    'ullong_sub':               None,
    'ullong_mul':               None,
    'ullong_div':               None,
    'ullong_truediv':           None,
    'ullong_floordiv':          None,
    'ullong_mod':               None,
    'ullong_lt':                None,
    'ullong_le':                None,
    'ullong_eq':                None,
    'ullong_ne':                None,
    'ullong_gt':                None,
    'ullong_ge':                None,

    'cast_bool_to_int':         None,
    'cast_bool_to_uint':        None,
    'cast_bool_to_float':       None,
    'cast_char_to_int':         None,
    'cast_unichar_to_int':      None,
    'cast_int_to_char':         None,
    'cast_int_to_unichar':      None,
    'cast_int_to_uint':         None,
    'cast_int_to_float':        None,
    'cast_int_to_longlong':     None,
    'cast_uint_to_int':         None,
    'cast_float_to_int':        None,
    'cast_float_to_uint':       None,
    'truncate_longlong_to_int': None
}
