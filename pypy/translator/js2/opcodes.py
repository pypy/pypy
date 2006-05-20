
""" opcode definitions
"""

from pypy.translator.cli.metavm import PushArg, PushAllArgs, StoreResult,\
     InstructionList, New, SetField, GetField, CallMethod, RuntimeNew, Call, MicroInstruction

DoNothing = [PushAllArgs]

class _SameAs ( MicroInstruction ):
    def render ( self , generator , op ):
        generator.change_name(op.result,op.args[0])
        
class _CastFloor ( MicroInstruction ):
    def render ( self , generator , op ):
        generator.cast_floor()

CastFloor = [ PushAllArgs , _CastFloor() ]
CopyName = [ PushAllArgs , _SameAs () ]
SameAs = CopyName

opcodes = {'int_mul': '*',
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
        
    'direct_call' : [Call],
    'same_as' : SameAs,
    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         CopyName,
    'cast_bool_to_uint':        CopyName,
    'cast_bool_to_float':       CopyName,
    'cast_char_to_int':         CopyName,
    'cast_unichar_to_int':      CopyName,
    'cast_int_to_char':         CopyName,
    'cast_int_to_unichar':      CopyName,
    'cast_int_to_uint':         CopyName,
    'cast_int_to_float':        CopyName,
    'cast_int_to_longlong':     CopyName,
    'cast_uint_to_int':         CopyName,
    'cast_float_to_int':        CastFloor,
    'cast_float_to_uint':       CastFloor,
    'truncate_longlong_to_int': CopyName,
}

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        if StoreResult not in value:
            value.append(StoreResult)
        value = InstructionList(value)

    opcodes[key] = value
