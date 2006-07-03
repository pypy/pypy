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
            'll_newlist' : lambda g,op: g.ilasm.load_const("[]"),
            'll_alloc_and_set' : CallBuiltin('alloc_and_set'),
            'get_document' : lambda g,op: g.ilasm.load_const('document'),
            'set_on_keydown' : SetOnEvent('onkeydown'),
            'set_on_keyup' : SetOnEvent('onkeyup'),
            'setTimeout' : SetTimeout,
            #'xmlSetCallback' : XmlSetCallback,
            'll_int_str' : lambda g,op: Call._render_builtin_method(g, 'toString' , [op.args[2]]),
            'll_strconcat' : InstructionList([PushAllArgs, '+']),
            'll_int' : CallBuiltin('parseInt'),
            #'ll_int' : lambda g,op: Call._render_builtin(g, 'parseInt', [op.args[0], op.args[0]]),
            'alert' : CallBuiltin('alert'),
            'seval' : CallBuiltin('seval'),
            'date': NewBuiltin('Date')
        }
        self.builtin_obj_map = {
            ootype.String.__class__: {
                'll_strconcat' : InstructionList([PushAllArgs, '+']),
                'll_strlen' : lambda g,op: GetBuiltinField.run_it(g, op.args[1], 'length'),
                'll_stritem_nonneg' : ListGetitem,
                'll_streq' : InstructionList([PushAllArgs, '==']),
                'll_strcmp' : CallBuiltin('strcmp'),
                'll_startswith' : CallBuiltin('startswith'),
                'll_endswith' : CallBuiltin('endswith'),
                'll_split_chr' : CallBuiltin('splitchr'),
                'll_substring' : lambda g,op: Call._render_builtin_method(g, 'substring', [op.args[1], op.args[2], op.args[3]])
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
            },
            ootype.Record: {
                'll_get' : ListGetitem,
                'll_set' : ListSetitem,
                'll_contains' : ListContains,
            }
        }

Builtins = _Builtins()
