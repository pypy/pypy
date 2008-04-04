""" JavaScript builtin mappings
"""

from pypy.translator.oosupport.metavm import InstructionList, PushAllArgs,\
     _PushAllArgs
from pypy.translator.js.metavm import SetBuiltinField, ListGetitem, ListSetitem, \
    GetBuiltinField, CallBuiltin, Call, SetTimeout, ListContains,\
    NewBuiltin, SetOnEvent, ListRemove, CallBuiltinMethod, _GetPredefinedField,\
    _SetPredefinedField

from pypy.rpython.ootypesystem import ootype

class _Builtins(object):
    def __init__(self):
        list_resize = _SetPredefinedField('length')
        
        self.builtin_map = {
            'll_js_jseval' : CallBuiltin('eval'),
            'set_on_keydown' : SetOnEvent('onkeydown'),
            'set_on_keyup' : SetOnEvent('onkeyup'),
            'setTimeout' : SetTimeout,
            'll_int_str' : CallBuiltinMethod('toString', [2]),
            'll_strconcat' : InstructionList([_PushAllArgs(slice(1, None)), '+']),
            'll_int' : CallBuiltin('parseInt'),
            #'alert' : CallBuiltin('alert'),
            'seval' : CallBuiltin('seval'),
            'date': NewBuiltin('Date'),
            'll_math.ll_math_fmod' : InstructionList([_PushAllArgs(slice(1, None)), '%']),
            'll_time_time' : CallBuiltin('time'),
            'll_time_clock' : CallBuiltin('clock'),
            'll_os_write' : CallBuiltin('print'),
            'll_math.ll_math_pow' : CallBuiltin('Math.pow'),
        }
        self.builtin_obj_map = {
            ootype.String.__class__: {
                'll_strconcat' : InstructionList([_PushAllArgs(slice(1, None)), '+']),
                'll_strlen' : _GetPredefinedField('length'),
                'll_stritem_nonneg' : CallBuiltinMethod('charAt', slice(1,None)),
                'll_streq' : InstructionList([_PushAllArgs(slice(1, None)), '==']),
                'll_strcmp' : CallBuiltin('strcmp'),
                'll_startswith' : CallBuiltin('startswith'),
                'll_endswith' : CallBuiltin('endswith'),
                'll_split_chr' : CallBuiltin('splitchr'),
                'll_substring' : CallBuiltin('substring'),
                'll_lower' : CallBuiltinMethod('toLowerCase', slice(1, None)),
                'll_upper' : CallBuiltinMethod('toUpperCase', slice(1, None)),
                'll_find' : CallBuiltin('findIndexOf'),
                'll_find_char' : CallBuiltin('findIndexOf'),
                'll_contains' : CallBuiltin('findIndexOfTrue'),
                'll_replace_chr_chr' : CallBuiltinMethod('replace', slice(1, None), ['g']),
                'll_count_char' : CallBuiltin('countCharOf'),
                'll_count' : CallBuiltin('countOf'),
            },
            ootype.List: {
                'll_setitem_fast' : ListSetitem,
                'll_getitem_fast' : ListGetitem,
                '_ll_resize' : list_resize,
                '_ll_resize_ge' : list_resize,
                '_ll_resize_le' : list_resize,
                'll_length' : _GetPredefinedField('length'),
            },
            ootype.Array: {
                'll_setitem_fast' : ListSetitem,
                'll_getitem_fast' : ListGetitem,
                'll_length' : _GetPredefinedField('length'),
            },
            ootype.Dict: {
                'll_get' : ListGetitem,
                'll_set' : ListSetitem,
                'll_contains' : ListContains,
                'll_get_items_iterator' : CallBuiltin('dict_items_iterator'),
                'll_length' : CallBuiltin('get_dict_len'),
                'll_remove' : ListRemove,
                'll_clear': CallBuiltin('clear_dict'),
            },
            ootype.Record: {
                'll_get' : ListGetitem,
                'll_set' : ListSetitem,
                'll_contains' : ListContains,
            }
        }
        self.fix_opcodes()

    def fix_opcodes(self):
        from pypy.translator.js.metavm import fix_opcodes
        #fix_opcodes(self.builtin_map)
        #for value in self.builtin_obj_map.values():
        #    fix_opcodes(value)

Builtins = _Builtins()
