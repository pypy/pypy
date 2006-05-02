from pypy.rpython.ootypesystem.ootype import List, Meth, Void

def get_method_name(graph, op):
    try:
        oopspec = graph.func.oopspec
    except AttributeError:
        return None

    # TODO: handle parsing of arguments; by now it is assumed that
    # builtin methods take the same arguments of the corresponding
    # ll_* function.
    full_name, _ = oopspec.split('(', 1)
    type_name, method_name = full_name.split('.')

    try:
        type_ = BUILTIN_TYPES[type_name]
    except KeyError:
        return None

    this = op.args[1]
    if isinstance(this.concretetype, type_) and method_name in BUILTIN_METHODS[type_]:
        return method_name
    else:
        return None # explicit is better than implicit :-)

def get_method(obj, name):
    try:
        return obj._GENERIC_METHODS[name]
    except KeyError:
        t = type(obj)
        return BUILTIN_METHODS[t][name]

BUILTIN_TYPES = {
    'list': List
    }

BUILTIN_METHODS = {
    List : {
        'Add': Meth([List.ITEMTYPE_T], Void)
        }
    } 
