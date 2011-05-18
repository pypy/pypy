from pypy.objspace.std import model, stdtypedef

_name_mappings = {
    'and': 'and_',
    'or': 'or_',
    }

def register_all(module_dict, *alt_ns):
    """register implementations for multimethods.

    By default a (name, object) pair of the given module dictionary
    is registered on the multimethod 'name' of StdObjSpace.
    If the name doesn't exist then the alternative namespace is tried
    for registration.
    """
    namespaces = list(alt_ns) + [model.MM]

    for name, obj in module_dict.items():
        if name.startswith('app_'):
            print "%s: direct app definitions deprecated" % name
        if name.find('__')<1 or name.startswith('app_'):
            continue
        funcname, sig = name.split('__')
        l = []
        for i in sig.split('_'):
            if i == 'ANY':        # just in case W_ANY is not in module_dict
                icls = model.W_ANY
            elif i == 'Object':   # just in case W_Object is not in module_dict
                icls = model.W_Object
            else:
                icls = (module_dict.get('W_%s' % i) or
                        module_dict.get('W_%sObject' % i))
                if icls is None:
                    x = module_dict.get(i)
                    if isinstance(x, stdtypedef.StdTypeDef):
                        icls = x.any
                if icls is None:
                    raise ValueError, \
                          "no W_%s or W_%sObject for the definition of %s" % (
                             i, i, name)
            l.append(icls)
        funcname =  _name_mappings.get(funcname, funcname)

        func = hack_func_by_name(funcname, namespaces)
        func.register(obj, *l)

    model.add_extra_comparisons()


def hack_func_by_name(funcname, namespaces):
    for ns in namespaces:
        if isinstance(ns, dict):
            if funcname in ns:
                return ns[funcname]
        else:
            if hasattr(ns, funcname):
                return getattr(ns, funcname)
    raise NameError, ("trying hard but not finding a multimethod named %s" %
                      funcname)
