from pypy.translator.cli.metavm import  Call, CallMethod, \
     IndirectCall, GetField, SetField, DownCast, NewCustomDict,\
     MapException, Box, Unbox, NewArray, GetArrayElem, SetArrayElem,\
     TypeOf, CastPrimitive, EventHandler, GetStaticField, SetStaticField, \
     DebugPrint
from pypy.translator.oosupport.metavm import PushArg, PushAllArgs, StoreResult, InstructionList,\
    New, RuntimeNew, CastTo, PushPrimitive, OOString, OOUnicode, OONewArray
from pypy.translator.cli.cts import WEAKREF
from pypy.rpython.ootypesystem import ootype

# some useful instruction patterns
Not = ['ldc.i4.0', 'ceq']
DoNothing = [PushAllArgs]
Ignore = []

def _not(op):
    return [PushAllArgs, op]+Not

def _abs(type_):
    return [PushAllArgs, 'call %s class [mscorlib]System.Math::Abs(%s)' % (type_, type_), StoreResult]

def _check_ovf(op, catch_arithmexic_exception=False):
    mapping = [('[mscorlib]System.OverflowException', 'exceptions.OverflowError')]
    if catch_arithmexic_exception:
        mapping.append(('[mscorlib]System.ArithmeticException', 'exceptions.OverflowError'))
    return [MapException(op, mapping)]

def _check_zer(op):
    mapping = [('[mscorlib]System.DivideByZeroException', 'exceptions.ZeroDivisionError')]
    return [MapException(op, mapping)]

def _check_ovf_zer(op):
    mapping = [('[mscorlib]System.OverflowException', 'exceptions.OverflowError'),
               ('[mscorlib]System.DivideByZeroException', 'exceptions.ZeroDivisionError'),
               ('[mscorlib]System.ArithmeticException', 'exceptions.OverflowError')]
    return [MapException(op, mapping)]

# __________ object oriented & misc operations __________
misc_ops = {
    'new':                      [New],
    'runtimenew':               [RuntimeNew],
    'oosetfield':               [SetField],
    'oogetfield':               [GetField],
    'oosend':                   [CallMethod],
    'ooupcast':                 DoNothing,
    'oodowncast':               [DownCast],
    'cast_to_object':           DoNothing,
    'cast_from_object':         [DownCast],
    'clibox':                   [Box],
    'cliunbox':                 [Unbox],
    'cli_newarray':             [NewArray],
    'cli_getelem':              [GetArrayElem],
    'cli_setelem':              [SetArrayElem],
    'cli_typeof':               [TypeOf],
    'cli_arraylength':          'ldlen',
    'cli_eventhandler':         [EventHandler],
    'cli_getstaticfield':       [GetStaticField],
    'cli_setstaticfield':       [SetStaticField],
    'classof':                  [PushAllArgs, 'callvirt instance class [mscorlib]System.Type object::GetType()'],
    'instanceof':               [CastTo, 'ldnull', 'cgt.un'],
    'subclassof':               [PushAllArgs, 'call bool [pypylib]pypy.runtime.Utils::SubclassOf(class [mscorlib]System.Type, class[mscorlib]System.Type)'],
    'gc_id':                    [PushAllArgs, 'call int32 [mscorlib]System.Runtime.CompilerServices.RuntimeHelpers::GetHashCode(object)'],   # XXX not implemented
    'gc_identityhash':          [PushAllArgs, 'call int32 [mscorlib]System.Runtime.CompilerServices.RuntimeHelpers::GetHashCode(object)'],
    'oostring':                 [OOString],
    'oounicode':                [OOUnicode],
    'ooparse_int':              [PushAllArgs, 'call int32 [pypylib]pypy.runtime.Utils::OOParseInt(string, int32)'],
    'ooparse_float':            [PushAllArgs, 'call float64 [pypylib]pypy.runtime.Utils::OOParseFloat(string)'],
    'oonewcustomdict':          [NewCustomDict],
    'oonewarray':               [OONewArray, StoreResult],
    
    'hint':                     [PushArg(0), StoreResult],
    'direct_call':              [Call],
    'indirect_call':            [IndirectCall],
    'int_between':              [PushAllArgs, 'call bool [pypylib]pypy.runtime.Utils::IntBetween(int32, int32, int32)'],


    'cast_ptr_to_weakadr':      [PushAllArgs, 'newobj instance void class %s::.ctor(object)' % WEAKREF],
    'gc__collect':              'call void class [mscorlib]System.GC::Collect()',
    'gc_set_max_heap_size':     Ignore,
    'debug_assert':             Ignore,
    'debug_start_traceback':    Ignore,
    'debug_record_traceback':   Ignore,
    'debug_catch_exception':    Ignore,
    'debug_reraise_traceback':  Ignore,
    'debug_print_traceback':    Ignore,
    'debug_print':              [DebugPrint],
    'debug_start':              [PushAllArgs, 'call void [pypylib]pypy.runtime.DebugPrint::DEBUG_START(string)'],
    'debug_stop':               [PushAllArgs, 'call void [pypylib]pypy.runtime.DebugPrint::DEBUG_STOP(string)'],
    'have_debug_prints':        [PushAllArgs, 'call bool [pypylib]pypy.runtime.DebugPrint::HAVE_DEBUG_PRINTS()'],
    'debug_fatalerror':         [PushAllArgs, 'call void [pypylib]pypy.runtime.Debug::DEBUG_FATALERROR(string)'],
    'keepalive':                Ignore,
    'jit_marker':               Ignore,
    'jit_force_virtualizable':  Ignore,
    'jit_force_virtual':        DoNothing,
    }

# __________ numeric operations __________

unary_ops = {
    'same_as':                  DoNothing,
    
    'bool_not':                 [PushAllArgs]+Not,

    'int_is_true':              [PushAllArgs, 'ldc.i4.0', 'cgt.un'],
    'int_neg':                  'neg',
    'int_neg_ovf':              _check_ovf(['ldc.i4.0', PushAllArgs, 'sub.ovf', StoreResult]),
    'int_abs':                  _abs('int32'),
    'int_abs_ovf':              _check_ovf(_abs('int32')),
    'int_invert':               'not',

    'uint_is_true':             [PushAllArgs, 'ldc.i4.0', 'cgt.un'],
    'uint_invert':              'not',

    'float_is_true':            [PushAllArgs, 'ldc.r8 0', 'ceq']+Not,
    'float_neg':                'neg',
    'float_abs':                _abs('float64'),

    'llong_is_true':            [PushAllArgs, 'ldc.i8 0', 'cgt.un'],
    'llong_neg':                'neg',
    'llong_neg_ovf':            _check_ovf(['ldc.i8 0', PushAllArgs, 'sub.ovf', StoreResult]),
    'llong_abs':                _abs('int64'),
    'llong_abs_ovf':            _check_ovf(_abs('int64')),
    'llong_invert':             'not',

    'ullong_is_true':            [PushAllArgs, 'ldc.i8 0', 'cgt.un'],
    'ullong_invert':             'not',

    'ooisnull':                 [PushAllArgs, 'ldnull', 'ceq'],
    'oononnull':                [PushAllArgs, 'ldnull', 'ceq']+Not,

    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         [PushAllArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_uint':        [PushAllArgs, 'ldc.i4.0', 'ceq']+Not,
    'cast_bool_to_float':       [PushAllArgs, 'ldc.i4.0', 'ceq']+Not+['conv.r8'],
    'cast_char_to_int':         DoNothing,
    'cast_unichar_to_int':      DoNothing,
    'cast_int_to_char':         DoNothing,
    'cast_int_to_unichar':      DoNothing,
    'cast_int_to_uint':         DoNothing,
    'cast_int_to_float':        'conv.r8',
    'cast_int_to_longlong':     'conv.i8',
    'cast_uint_to_int':         DoNothing,
    'cast_uint_to_float':       [PushAllArgs, 'conv.u8', 'conv.r8'],
    'cast_float_to_int':        'conv.i4',
    'cast_float_to_uint':       'conv.u4',
    'cast_longlong_to_float':   'conv.r8',
    'cast_float_to_longlong':   'conv.i8',
    'cast_ulonglong_to_float':  'conv.r8',
    'cast_float_to_ulonglong':  'conv.u8',
    'cast_primitive':           [PushAllArgs, CastPrimitive],
    'force_cast':               [PushAllArgs, CastPrimitive],
    'truncate_longlong_to_int': 'conv.i4',
    }

binary_ops = {
    'char_lt':                  'clt',
    'char_le':                  _not('cgt'),
    'char_eq':                  'ceq',
    'char_ne':                  _not('ceq'),
    'char_gt':                  'cgt',
    'char_ge':                  _not('clt'),

    'unichar_eq':               'ceq',
    'unichar_ne':               _not('ceq'),

    'int_add':                  'add',
    'int_sub':                  'sub',
    'int_mul':                  'mul',
    'int_floordiv':             'div',
    'int_floordiv_zer':         _check_zer('div'),
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
    'int_add_ovf':              _check_ovf('add.ovf'),
    'int_add_nonneg_ovf':       _check_ovf('add.ovf'),
    'int_sub_ovf':              _check_ovf('sub.ovf'),
    'int_mul_ovf':              _check_ovf('mul.ovf'),
    'int_floordiv_ovf':         _check_ovf('div', catch_arithmexic_exception=True),
    'int_mod_ovf':              _check_ovf('rem', catch_arithmexic_exception=True),
    'int_lt_ovf':               'clt',
    'int_le_ovf':               _not('cgt'),
    'int_eq_ovf':               'ceq',
    'int_ne_ovf':               _not('ceq'),
    'int_gt_ovf':               'cgt',
    'int_ge_ovf':               _not('clt'),
    'int_and_ovf':              'and',
    'int_or_ovf':               'or',

    'int_lshift_ovf':           _check_ovf([PushArg(0),'conv.i8',PushArg(1), 'shl',
                                            'conv.ovf.i4', StoreResult]),

    'int_rshift_ovf':           'shr', # these can't overflow!
    'int_xor_ovf':              'xor',
    'int_floordiv_ovf_zer':     _check_ovf_zer('div'),
    'int_mod_ovf_zer':          _check_ovf_zer('rem'),
    'int_mod_zer':              _check_zer('rem'),

    'uint_add':                 'add',
    'uint_sub':                 'sub',
    'uint_mul':                 'mul',
    'uint_div':                 'div.un',
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

    'float_add':                'add',
    'float_sub':                'sub',
    'float_mul':                'mul',
    'float_truediv':            'div', 
    'float_lt':                 'clt',
    'float_le':                 _not('cgt'),
    'float_eq':                 'ceq',
    'float_ne':                 _not('ceq'),
    'float_gt':                 'cgt',
    'float_ge':                 _not('clt'),

    'llong_add':                'add',
    'llong_sub':                'sub',
    'llong_mul':                'mul',
    'llong_div':                'div',
    'llong_floordiv':           'div',
    'llong_floordiv_zer':       _check_zer('div'),
    'llong_mod':                'rem',
    'llong_mod_zer':            _check_zer('rem'),
    'llong_lt':                 'clt',
    'llong_le':                 _not('cgt'),
    'llong_eq':                 'ceq',
    'llong_ne':                 _not('ceq'),
    'llong_gt':                 'cgt',
    'llong_ge':                 _not('clt'),
    'llong_and':                'and',
    'llong_or':                 'or',
    'llong_lshift':             'shl',
    'llong_rshift':             [PushAllArgs, 'conv.i4', 'shr'],
    'llong_xor':                'xor',

    'ullong_add':               'add',
    'ullong_sub':               'sub',
    'ullong_mul':               'mul',
    'ullong_div':               'div.un',
    'ullong_floordiv':          'div.un',
    'ullong_mod':               'rem.un',
    'ullong_lt':                'clt.un',
    'ullong_le':                _not('cgt.un'),
    'ullong_eq':                'ceq',
    'ullong_ne':                _not('ceq'),
    'ullong_gt':                'cgt.un',
    'ullong_ge':                _not('clt.un'),
    'ullong_lshift':            [PushAllArgs, 'conv.u4', 'shl'],
    'ullong_rshift':            [PushAllArgs, 'conv.i4', 'shr'],
    'ullong_and':               'and',
    'ullong_or':                'or',

    'oois':                     'ceq',
    'ooisnot':                  _not('ceq'),
}

opcodes = misc_ops.copy()
opcodes.update(unary_ops)
opcodes.update(binary_ops)

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        if value is not Ignore and StoreResult not in value and not isinstance(value[0], MapException):
            value.append(StoreResult)
        value = InstructionList(value)

    opcodes[key] = value

