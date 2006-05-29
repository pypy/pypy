
""" several builtins mapping
"""

from pypy.rpython.ootypesystem.ootype import List, Meth, Void, String

from pypy.translator.js2.log import log

import re

SETITEM = 1

class _Builtins(object):
    BUILTIN_MAP = {
        'js_jseval' : ('eval', False),
        'newlist' : ('[]', True),
        'alloc_and_set' : ('alloc_and_set', False),
        'strconcat' : ('strconcat', False),
        'stritem' : ('stritem', False),
        'delitem_nonneg' : ('delitem', False),
        'streq' : 'equal',
        'strcmp' : ('strcmp', False),
        'startswith' : ('startswith', False),
        'endswith' : ('endswith', False),
    }

    BUILTIN_METHOD_MAP = {
        List: {
            'll_setitem_fast' : 'list_ll_setitem',
            'll_getitem_fast' : 'list_ll_getitem',
            '_ll_resize' : 'list_ll_resize',
            '_ll_resize_ge' : 'list_ll_resize',
            '_ll_resize_le' : 'list_ll_resize',
            'll_length' : ('length', True),
        },
        String.__class__: {
            'll_strlen' : ('length', True),
            'll_stritem_nonneg' : 'list_ll_getitem',
        }
    }
    
    def real_name(self, _name):
        name = _name.split('__')[0]
        m = re.match("^ll_(.*)$", name)
        if not m:
            return None
        return m.group(1)

    def map_builtin_function(self, const, inst, args, generator):
        name = self.real_name(const.value._name)
        if name is None:
            return None
        
        if getattr(const.value, 'suggested_primitive', False):
            log("Suggested primitive %r"%const)
        try:
            model = self.BUILTIN_MAP[name]
            if isinstance(model, tuple):
                return model
            else:
                getattr(inst, model)(None, args, generator)
                return False
        except KeyError:
            return None

    def map_builtin_method(self, base_obj, method, args, inst, generator):
        try:
            log("Baseobj: %r, method: %r"%(base_obj.concretetype, method))
            model = self.BUILTIN_METHOD_MAP[base_obj.concretetype.__class__][method]
            if isinstance(model,tuple):
                log("Suggested simple mapping %r"%(model,))
                return model
            else:
                getattr(inst, model)(base_obj, args, generator)
            return False
        except KeyError:
            return None

Builtins = _Builtins()
