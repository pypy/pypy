from pypy.translator.cli.metavm import PushArg, PushAllArgs,\
     StoreResult, Call, InstructionList, New, SetField, GetField, CallMethod

# some useful instruction patterns
Not = ['ldc.i4.0', 'ceq']
DoNothing = [PushAllArgs]

def _not(op):
    return [PushAllArgs, op]+Not

def _abs(type_):
    return [PushAllArgs, 'call %s class [mscorlib]System.Math::Abs(%s)' % (type_, type_)]


opcodes = {
    # __________ object oriented operations __________
    'new':                      [New],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField],
    'oosend':                   [CallMethod],
    'ooupcast':                 DoNothing,
    'oodowncast':               DoNothing, # TODO: is it really safe?

    
    'same_as':                  DoNothing, # TODO: does same_as really do nothing else than renaming?    
    'direct_call':              [Call],
    'indirect_call':            None,      # when is it generated?

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
    'int_neg_ovf':              ['ldc.i4.0', PushAllArgs, 'sub.ovf'],
    'int_abs':                  _abs('int32'),
    'int_abs_ovf':              _abs('int32'),
    'int_invert':               'not',

    'int_add':                  'add',
    'int_sub':                  'sub',
    'int_mul':                  'mul',
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
    'int_add_ovf':              'add.ovf',
    'int_sub_ovf':              'sub.ovf',
    'int_mul_ovf':              'mul.ovf',
    'int_floordiv_ovf':         'div', # these can't overflow!
    'int_mod_ovf':              'rem',
    'int_lt_ovf':               'clt',
    'int_le_ovf':               _not('cgt'),
    'int_eq_ovf':               'ceq',
    'int_ne_ovf':               _not('ceq'),
    'int_gt_ovf':               'cgt',
    'int_ge_ovf':               _not('clt'),
    'int_and_ovf':              'and',
    'int_or_ovf':               'or',

    # are they the same?
    'int_lshift_ovf':           [PushArg(0), 'conv.i8', PushArg(1), 'shl', 'conv.ovf.i4'],
    'int_lshift_ovf_val':       [PushArg(0), 'conv.i8', PushArg(1), 'shl', 'conv.ovf.i4'],

    'int_rshift_ovf':           'shr', # these can't overflow!
    'int_xor_ovf':              'xor',
    'int_floordiv_ovf_zer':     None,  # what's the meaning?
    'int_mod_ovf_zer':          None,

    'uint_is_true':             DoNothing,
    'uint_neg':                 None,      # What's the meaning?
    'uint_abs':                 _abs('unsigned int32'), # TODO: ?
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

    'float_is_true':            [PushAllArgs, 'ldc.r8 0', 'ceq']+Not,
    'float_neg':                'neg',
    'float_abs':                _abs('float64'),

    'float_add':                'add',
    'float_sub':                'sub',
    'float_mul':                'mul',
    'float_truediv':            'div', 
    'float_mod':                'rem',
    'float_lt':                 'clt',
    'float_le':                 _not('cgt'),
    'float_eq':                 'ceq',
    'float_ne':                 _not('ceq'),
    'float_gt':                 'cgt',
    'float_ge':                 _not('clt'),
    'float_floor':              None, # TODO
    'float_fmod':               None, # TODO

    'llong_is_true':            [PushAllArgs, 'ldc.i8 0', 'ceq']+Not,
    'llong_neg':                'neg',
    'llong_abs':                _abs('int64'),
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

    'ullong_is_true':            [PushAllArgs, 'ldc.i8 0', 'ceq']+Not,
    'ullong_neg':                None,
    'ullong_abs':                _abs('unsigned int64'),
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
    'cast_bool_to_int':         [PushAllArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_uint':        [PushAllArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_float':       [PushAllArgs, 'ldc.i4 0', 'ceq']+Not+['conv.r8'],
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

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        value = InstructionList(value + [StoreResult])
        
    opcodes[key] = value

