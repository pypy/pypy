DoNothing = object()
PushArgs = object()

# come useful instruction patterns
Not = ['ldc.i4.0', 'ceq']

def _not(op):
    return [PushArgs, op]+Not


opcodes = {
    'same_as':                  DoNothing, # TODO: does same_as really do nothing else than renaming?    
    'direct_call':              None,      # for now it's a special case
    'indirect_call':            None,      # when it's generated?

    # __________ numeric operations __________

    'bool_not':                 Not,

    'char_lt':                  None,
    'char_le':                  None,
    'char_eq':                  None,
    'char_ne':                  None,
    'char_gt':                  None,
    'char_ge':                  None,

    'unichar_eq':               None,      # should we unify unichar and char, as Jython does?
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

    'uint_is_true':             DoNothing,
    'uint_neg':                 None,      # What's the meaning?
    'uint_abs':                 None, # TODO
    'uint_invert':              'not',

    'uint_add':                 'add',
    'uint_sub':                 'sub',
    'uint_mul':                 'mul',
    'uint_div':                 'div.un',
    'uint_truediv':             None, # TODO
    'uint_floordiv':            'div.un',
    'uint_mod':                 'rem.un',
    'uint_lt':                  'clt.un',
    'uint_le':                  _not('cgt.un'),
    'uint_eq':                  'ceq',
    'uint_ne':                  _not('ceq'),
    'uint_gt':                  'cgt.un',
    'uint_ge':                  _not('clt.un'),
    'uint_and':                 'and',
    'uint_or':                  'or',
    'uint_lshift':              'shl',
    'uint_rshift':              'shr.un',
    'uint_xor':                 'xor',

    'float_is_true':            [PushArgs, 'ldc.r8 0', 'ceq']+Not,
    'float_neg':                'neg',
    'float_abs':                None, # TODO

    'float_add':                'add',
    'float_sub':                'sub',
    'float_mul':                'mul',
    'float_div':                'div',
    'float_truediv':            'div', 
    'float_floordiv':           None, # TODO
    'float_mod':                'rem',
    'float_lt':                 'clt',
    'float_le':                 _not('cgt'),
    'float_eq':                 'ceq',
    'float_ne':                 _not('ceq'),
    'float_gt':                 'cgt',
    'float_ge':                 _not('clt'),
    'float_floor':              None, # TODO
    'float_fmod':               None, # TODO

    'llong_is_true':            [PushArgs, 'ldc.i8 0', 'ceq']+Not,
    'llong_neg':                'neg',
    'llong_abs':                None, # TODO
    'llong_invert':             'not',

    'llong_add':                'add',
    'llong_sub':                'sub',
    'llong_mul':                'mul',
    'llong_div':                'div',
    'llong_truediv':            None, # TODO
    'llong_floordiv':           'div',
    'llong_mod':                'rem',
    'llong_lt':                 'clt',
    'llong_le':                 _not('cgt'),
    'llong_eq':                 'ceq',
    'llong_ne':                 _not('ceq'),
    'llong_gt':                 'cgt',
    'llong_ge':                 _not('clt'),

    'ullong_is_true':            [PushArgs, 'ldc.i8 0', 'ceq']+Not,
    'ullong_neg':                None,
    'ullong_abs':                None, # TODO
    'ullong_invert':             'not',

    'ullong_add':               'add',
    'ullong_sub':               'sub',
    'ullong_mul':               'mul',
    'ullong_div':               'div.un',
    'ullong_truediv':           None, # TODO
    'ullong_floordiv':          'div.un',
    'ullong_mod':               'rem.un',
    'ullong_lt':                'clt.un',
    'ullong_le':                _not('cgt.un'),
    'ullong_eq':                'ceq',
    'ullong_ne':                _not('ceq.un'),
    'ullong_gt':                'cgt.un',
    'ullong_ge':                _not('clt.un'),

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         [PushArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_uint':        [PushArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_float':       [PushArgs, 'ldc.i4 0', 'ceq']+Not+['conv.r8'],
    'cast_char_to_int':         None,
    'cast_unichar_to_int':      None,
    'cast_int_to_char':         None,
    'cast_int_to_unichar':      None,
    'cast_int_to_uint':         DoNothing,
    'cast_int_to_float':        'conv.r8',
    'cast_int_to_longlong':     'conv.i8',
    'cast_uint_to_int':         DoNothing,
    'cast_float_to_int':        'conv.i4',
    'cast_float_to_uint':       'conv.i4',
    'truncate_longlong_to_int': 'conv.i4',
}
