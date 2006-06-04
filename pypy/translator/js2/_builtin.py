
""" several builtins mapping
"""

from pypy.rpython.ootypesystem.ootype import List, Meth, Void, String, Instance

from pypy.translator.js2.log import log

import re

SETITEM = 1

class _Builtins(object):
    # Returns builtin function mapping + property flag or attribute to call (plain string)
    BUILTIN_MAP = {
        'll_js_jseval' : ('eval', False),
        'll_newlist' : ('[]', True),
        'll_alloc_and_set' : ('alloc_and_set', False),
        'll_strconcat' : ('strconcat', False),
        'll_stritem' : ('stritem', False),
        'll_delitem_nonneg' : ('delitem', False),
        'll_streq' : ['equal'],
        'll_strcmp' : ('strcmp', False),
        'll_startswith' : ('startswith', False),
        'll_endswith' : ('endswith', False),
        'll_int' : ('parseInt', False),
        'get_document' : ('document', True),
    }

    BUILTIN_METHOD_MAP = {
        List: {
            'll_setitem_fast' : ['list_ll_setitem'],
            'll_getitem_fast' : ['list_ll_getitem'],
            '_ll_resize' : ['list_ll_resize'],
            '_ll_resize_ge' : ['list_ll_resize'],
            '_ll_resize_le' : ['list_ll_resize'],
            'll_length' : ('length', True),
        },
        String.__class__: {
            'll_strlen' : ('length', True),
            'll_stritem_nonneg' : ['list_ll_getitem'],
        }
    }
    
    # Return builtin class/method property mapping + getter/setter flag
    BUILTINS_METHOD_PROPERTY_MAP = {
        'dom.Node': {
            'setInnerHTML' : ('innerHTML', True),
        }
    }
    
    def real_name(self, _name):
        return _name.split('__')[0]

    def map_builtin_function(self, const, inst, args, generator):
        name = self.real_name(const.value._name)
        
        if getattr(const.value, 'suggested_primitive', False):
            log("Suggested primitive %r"%const)
        try:
            model = self.BUILTIN_MAP[name]
            if isinstance(model, tuple):
                return model
            else:
                getattr(inst, model[0])(None, args, generator, *model[1:])
                return False
        except KeyError:
            return None

    def is_builtin_object(self, _class, obj, method, args):
        if not _class is Instance:
            return None
        m = re.search("js2\.modules\.(.*)", obj.concretetype._name)
        if m:
            real_name = obj.concretetype._methods[method]._name[1:]
            try:
                # We define property and property setters here
                name,val = self.BUILTINS_METHOD_PROPERTY_MAP[m.group(1)][real_name]
                if val:
                    return ['setitem',name]
                return name, True
            except KeyError:
                return real_name, False
        return None

    def map_builtin_method(self, base_obj, method, args, inst, generator):
        try:
            log("Baseobj: %r, method: %r"%(base_obj.concretetype, method))
            model = self.is_builtin_object(base_obj.concretetype.__class__, base_obj, method, args)
            if not model:
                model = self.BUILTIN_METHOD_MAP[base_obj.concretetype.__class__][method]
            if isinstance(model,tuple):
                log("Suggested simple mapping %r"%(model,))
                return model
            else:
                getattr(inst, model[0])(base_obj, args, generator, *model[1:])
            return False
        except KeyError:
            return None

Builtins = _Builtins()
