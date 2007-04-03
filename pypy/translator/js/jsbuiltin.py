""" JavaScript builtin mappings
"""

from pypy.translator.oosupport.metavm import InstructionList, PushAllArgs
from pypy.translator.js.metavm import SetBuiltinField, ListGetitem, ListSetitem, \
    GetBuiltinField, CallBuiltin, Call, SetTimeout, ListContains,\
    NewBuiltin, SetOnEvent

from pypy.rpython.ootypesystem import ootype

class _Builtins(object):
    def __init__(self):
        list_resize = lambda g,op: SetBuiltinField.run_it(g, op.args[1], 'length', op.args[2])
        
        self.builtin_map = {
            'll_js_jseval' : CallBuiltin('eval'),
            'set_on_keydown' : SetOnEvent('onkeydown'),
            'set_on_keyup' : SetOnEvent('onkeyup'),
            'setTimeout' : SetTimeout,
            'll_int_str' : lambda g,op: Call._render_builtin_method(g, 'toString' , [op.args[2]]),
            'll_strconcat' : InstructionList([PushAllArgs, '+']),
            'll_int' : CallBuiltin('parseInt'),
            #'alert' : CallBuiltin('alert'),
            'seval' : CallBuiltin('seval'),
            'date': NewBuiltin('Date'),
            'll_math.ll_math_fmod' : InstructionList([PushAllArgs, '%']),
            'll_time_time' : CallBuiltin('time'),
            'll_time_clock' : CallBuiltin('clock'),
            'll_os_write' : CallBuiltin('print'),
        }
        self.builtin_obj_map = {
            ootype.String.__class__: {
                'll_strconcat' : InstructionList([PushAllArgs, '+']),
                'll_strlen' : lambda g,op: GetBuiltinField.run_it(g, op.args[1], 'length'),
                'll_stritem_nonneg' : lambda g, op: Call._render_builtin_method(g, 'charAt', [op.args[1], op.args[2]]),
                'll_streq' : InstructionList([PushAllArgs, '==']),
                'll_strcmp' : CallBuiltin('strcmp'),
                'll_startswith' : CallBuiltin('startswith'),
                'll_endswith' : CallBuiltin('endswith'),
                'll_split_chr' : CallBuiltin('splitchr'),
                #'ll_substring' : lambda g,op: Call._render_builtin_method(g, 'substring', [op.args[1], op.args[2], op.args[3]]),
                'll_substring' : CallBuiltin('substring'),
                'll_lower' : lambda g, op: Call._render_builtin_method(g, 'toLowerCase', [op.args[1]]),
                'll_upper' : lambda g, op: Call._render_builtin_method(g, 'toUpperCase', [op.args[1]]),
                'll_find' : CallBuiltin('findIndexOf'),
                'll_find_char' : CallBuiltin('findIndexOf'),
                #'ll_find' : lambda g, op: Call._render_builtin_method(g, 'indexOf', [op.args[1], op.args[2], op.args[3]]),
                #'ll_find_char' : lambda g, op: Call._render_builtin_method(g, 'indexOf', [op.args[1], op.args[2], op.args[3]]),
                'll_contains' : CallBuiltin('findIndexOfTrue'),
                'll_replace_chr_chr' : lambda g, op:
                     Call._render_builtin_method(g, 'replace',
                     [op.args[1], op.args[2], op.args[3], 'g']),
                'll_count_char' : CallBuiltin('countCharOf'),
                'll_count' : CallBuiltin('countOf'),
            },
            ootype.List: {
                'll_setitem_fast' : ListSetitem,
                'll_getitem_fast' : ListGetitem,
                '_ll_resize' : list_resize,
                '_ll_resize_ge' : list_resize,
                '_ll_resize_le' : list_resize,
                'll_length' : lambda g,op: GetBuiltinField.run_it(g, op.args[1], 'length'),
            },
            ootype.Dict: {
                'll_get' : ListGetitem,
                'll_set' : ListSetitem,
                'll_contains' : ListContains,
                'll_get_items_iterator' : CallBuiltin('dict_items_iterator'),
                'll_length' : CallBuiltin('get_dict_len'),
                'll_remove' : lambda g, op: CallBuiltin('delete')._render_builtin_prepared_args(g, 'delete', ['%s[%s]' % (op.args[1], op.args[2])]),
                'll_clear': CallBuiltin('clear_dict'),
            },
            ootype.Record: {
                'll_get' : ListGetitem,
                'll_set' : ListSetitem,
                'll_contains' : ListContains,
            }
        }

Builtins = _Builtins()
