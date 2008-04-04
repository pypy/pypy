from pypy.rpython.ootypesystem import ootype

def get_method_name(graph, op):
    try:
        oopspec = graph.func.oopspec
    except AttributeError:
        return None

    # TODO: handle parsing of arguments; by now it is assumed that
    # builtin methods take the same arguments of the corresponding
    # ll_* function.
    full_name, _ = oopspec.split('(', 1)

    if len(full_name.split('.')) != 2:
        return None
    try:
        type_name, method_name = full_name.split('.')
    except ValueError:
        return None

    try:
        type_ = BUILTIN_TYPES[type_name]
    except KeyError:
        return None

    this = op.args[1]
    if isinstance(this.concretetype, type_) and method_name in BUILTIN_METHODS[type_]:
        return method_name
    else:
        return None # explicit is better than implicit :-)

def get_method(TYPE, name):
    try:
        # special case: when having List of Void, or an Array, look at
        # the concrete methods, not the generic ones
        if isinstance(TYPE, ootype.Array) or (isinstance(TYPE, ootype.List) and TYPE.ITEM is ootype.Void):
            return TYPE._METHODS[name]
        else:
            return TYPE._GENERIC_METHODS[name]
    except KeyError:
        t = type(TYPE)
        return BUILTIN_METHODS[t][name]

BUILTIN_TYPES = {
    'list': ootype.List
    }

BUILTIN_METHODS = {
    ootype.List : {
        'Add': ootype.Meth([ootype.List.ITEMTYPE_T], ootype.Void)
        }
    } 
