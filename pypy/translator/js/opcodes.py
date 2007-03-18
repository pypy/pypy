""" opcode definitions
"""

from pypy.translator.oosupport.metavm import PushArg, PushAllArgs, StoreResult,\
    InstructionList, New, SetField, GetField, MicroInstruction, RuntimeNew
     
from pypy.translator.oosupport.metavm import _GetFieldDispatcher, _SetFieldDispatcher, \
    _CallDispatcher, _MethodDispatcher

from pypy.translator.js.metavm import SameAs, IsInstance, Call, CallMethod, CopyName, CastString,\
    _Prefix, _CastFun, _NotImplemented, CallBuiltin, CallBuiltinObject, GetBuiltinField, SetBuiltinField,\
    IndirectCall, CallExternalObject, SetExternalField, _CastMethod, _LoadConst

from pypy.translator.js.jsbuiltin import Builtins

DoNothing = [PushAllArgs]

from pypy.translator.js.log import log

class_map = { 'Call' : Call,
    'CallMethod' : CallMethod,
    'CallBuiltinObject' : CallBuiltinObject,
    'CallBuiltin' : CallBuiltin,
    'GetBuiltinField' : GetBuiltinField,
    'GetField' : GetField,
    'SetField' : SetField,
    'SetBuiltinField' : SetBuiltinField,
    'CallExternalObject' : CallExternalObject,
    'SetExternalField' : SetExternalField,
}

opcodes = {'int_mul': '*',
    'int_add': '+',
    'int_sub': '-',
    'int_sub_ovf': '-', # XXX overflow
    'int_floordiv': '/',
    'int_mod': '%',
    'int_mod_ovf': '%', # XXX: what's that?
    'int_mod_zer': '%', # XXX: fix zero stuff
    'int_and': '&',
    'int_or': '|',
    'int_xor': '^',
    'int_lshift': '<<',
    'int_lshift_ovf': '<<', # XXX overflow
    'int_rshift': '>>',
    'int_rshift_ovf': '>>', # XXX overflow
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
    
    'char_lt': '<',
    'char_le': '<=',
    'char_eq': '==',
    'char_ne': '!=',
    'char_ge': '>=',
    'char_gt': '>',

    'float_mul': '*',
    'float_add': '+',
    'float_sub': '-',
    'float_truediv': '/',
    'float_lt': '<',
    'float_le': '<=',
    'float_eq': '==',
    'float_ne': '!=',
    'float_ge': '>=',
    'float_gt': '>',

    'ptr_eq': '==',
    'ptr_ne': '!=',

    'bool_not': [PushAllArgs,_Prefix('!')],
    'int_neg': [PushAllArgs,_Prefix('-')],
    'int_invert': [PushAllArgs,_Prefix('~')],
    'float_neg': [PushAllArgs,_Prefix('-')],
        
    'float_pow': [PushAllArgs,_CastFun('Math.pow',2)],
    'int_abs': [PushAllArgs,_CastFun('Math.abs',1)],
    'float_abs': [PushAllArgs,_CastFun('Math.abs',1)],

    'int_is_true': [PushAllArgs,_Prefix('!!')],
    'uint_is_true': [PushAllArgs,_Prefix('!!')],
    'float_is_true': [PushAllArgs,_Prefix('!!')],
    'is_true': [PushAllArgs,_Prefix('!!')],
    
    'direct_call' : [_CallDispatcher(Builtins, class_map)],
    'indirect_call' : [IndirectCall],
    'same_as' : SameAs,
    'new' : [New],
    'runtimenew' : [RuntimeNew],
    'instanceof' : [IsInstance],
    
    # objects
    
    'oosetfield' : [_SetFieldDispatcher(Builtins, class_map)],
    'oogetfield' : [_GetFieldDispatcher(Builtins, class_map)],
    'oosend'     : [_MethodDispatcher(Builtins, class_map)],
    #'ooupcast'   : [_NotImplemented("Inheritance not implemented (ooupcast)")],
    #'oodowncast' : [_NotImplemented("Inheritance not implemented (oodowncast)")],
    'ooupcast'   : DoNothing,
    'oodowncast' : DoNothing,        
    'oononnull'  : [PushAllArgs,_Prefix('!!')],
    'oostring'   : [PushArg(0),CastString],
    'ooparse_int' : [PushAllArgs,_CastFun("parseInt",2)],
    'oois'       : '===',
    # when casting from bool we want that every truth value is casted
    # to 1: we can't simply DoNothing, because the CLI stack could
    # contains a truth value not equal to 1, so we should use the !=0
    # trick.
    'cast_bool_to_int':         CopyName,
    'cast_bool_to_uint':        CopyName,
    'cast_bool_to_float':       CopyName,
    'cast_char_to_int':         [PushAllArgs,_LoadConst(0),_CastMethod("charCodeAt",1)],
    'cast_unichar_to_int':      [PushAllArgs,_LoadConst(0),_CastMethod("charCodeAt",1)],
    'cast_int_to_char':         [PushAllArgs,_CastFun("String.fromCharCode",1)],
    'cast_int_to_unichar':      [PushAllArgs,_CastFun("String.fromCharCode",1)],
    'cast_int_to_uint':         CopyName,
    'cast_int_to_float':        CopyName,
    'cast_int_to_longlong':     CopyName,
    'cast_uint_to_int':         CopyName,
    'cast_uint_to_float':       CopyName,
    'cast_float_to_int':        [PushAllArgs,_CastFun("Math.floor",1)],
    'cast_float_to_uint':       [PushAllArgs,_CastFun("Math.floor",1)],
    'truncate_longlong_to_int': CopyName,
    
    'debug_assert' : DoNothing,
    'resume_point' : DoNothing,
}

for key, value in opcodes.iteritems():
    if type(value) is str:
        value = InstructionList([PushAllArgs, value, StoreResult])
    elif value is not None:
        if StoreResult not in value:
            value.append(StoreResult)
        value = InstructionList(value)

    opcodes[key] = value
