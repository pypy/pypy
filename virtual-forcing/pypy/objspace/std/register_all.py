
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
    from pypy.objspace.std.objspace import StdObjSpace
    from pypy.objspace.std.model import W_ANY, W_Object
    from pypy.objspace.std.stdtypedef import StdTypeDef
    namespaces = list(alt_ns) + [StdObjSpace.MM, StdObjSpace]

    for name, obj in module_dict.items():
        if name.startswith('app_'): 
            print "%s: direct app definitions deprecated" % name 
        if name.find('__')<1 or name.startswith('app_'):
            continue
        funcname, sig = name.split('__')
        l=[]
        for i in sig.split('_'):
            if i == 'ANY':        # just in case W_ANY is not in module_dict
                icls = W_ANY
            elif i == 'Object':   # just in case W_Object is not in module_dict
                icls = W_Object
            else:
                icls = (module_dict.get('W_%s' % i) or
                        module_dict.get('W_%sObject' % i))
                if icls is None:
                    x = module_dict.get(i)
                    if isinstance(x, StdTypeDef):
                        icls = x.any
                if icls is None:
                    raise ValueError, \
                          "no W_%s or W_%sObject for the definition of %s" % (
                             i, i, name)
            l.append(icls)

        #XXX trying to be too clever at the moment for userobject.SpecialMethod
        #if len(l) != obj.func_code.co_argcount-1:
        #    raise ValueError, \
        #          "function name %s doesn't specify exactly %d arguments" % (
        #             repr(name), obj.func_code.co_argcount-1)

        funcname =  _name_mappings.get(funcname, funcname)

        func = hack_func_by_name(funcname, namespaces)
        func.register(obj, *l)

    add_extra_comparisons()


def hack_func_by_name(funcname, namespaces):
    for ns in namespaces:
        if isinstance(ns, dict):
            if funcname in ns:
                return ns[funcname]
        else:
            if hasattr(ns, funcname):
                return getattr(ns, funcname)
    #import typetype
    #try:
    #    return getattr(typetype.W_TypeType, funcname)
    #except AttributeError:
    #    pass  # catches not only the getattr() but the typetype.W_TypeType
    #          # in case it is not fully imported yet :-((((
    from pypy.objspace.std import objecttype
    try:
        return getattr(objecttype, funcname)
    except AttributeError:
        pass
    raise NameError, ("trying hard but not finding a multimethod named %s" %
                      funcname)


def op_negated(function):
    def op(space, w_1, w_2):
        return space.not_(function(space, w_1, w_2))
    return op

def op_swapped(function):
    def op(space, w_1, w_2):
        return function(space, w_2, w_1)
    return op

def op_swapped_negated(function):
    def op(space, w_1, w_2):
        return space.not_(function(space, w_2, w_1))
    return op

OPERATORS = ['lt', 'le', 'eq', 'ne', 'gt', 'ge']
OP_CORRESPONDANCES = [
    ('eq', 'ne', op_negated),
    ('lt', 'gt', op_swapped),
    ('le', 'ge', op_swapped),
    ('lt', 'ge', op_negated),
    ('le', 'gt', op_negated),
    ('lt', 'le', op_swapped_negated),
    ('gt', 'ge', op_swapped_negated),
    ]
for op1, op2, value in OP_CORRESPONDANCES[:]:
    i = OP_CORRESPONDANCES.index((op1, op2, value))
    OP_CORRESPONDANCES.insert(i+1, (op2, op1, value))

def add_extra_comparisons():
    """
    Add the missing comparison operators if they were not explicitly
    defined:  eq <-> ne  and  lt <-> le <-> gt <-> ge.
    We try to add them in the order defined by the OP_CORRESPONDANCES
    table, thus favouring swapping the arguments over negating the result.
    """
    from pypy.objspace.std.objspace import StdObjSpace
    originalentries = {}
    for op in OPERATORS:
        originalentries[op] = getattr(StdObjSpace.MM, op).signatures()

    for op1, op2, correspondance in OP_CORRESPONDANCES:
        mirrorfunc = getattr(StdObjSpace.MM, op2)
        for types in originalentries[op1]:
            t1, t2 = types
            if t1 is t2:
                if not mirrorfunc.has_signature(types):
                    functions = getattr(StdObjSpace.MM, op1).getfunctions(types)
                    assert len(functions) == 1, ('Automatic'
                            ' registration of comparison functions'
                            ' only work when there is a single method for'
                            ' the operation.')
                    #print 'adding %s <<<%s>>> %s as %s(%s)' % (
                    #    t1, op2, t2,
                    #    correspondance.func_name, functions[0].func_name)
                    mirrorfunc.register(
                        correspondance(functions[0]),
                        *types)
