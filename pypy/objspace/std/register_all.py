
_name_mappings = {
    'and': 'and_',
    'or': 'or_',
    'not': 'not_',
    }
    
def register_all(module_dict, alt_ns=None):
    """register implementations for multimethods. 

    By default a (name, object) pair of the given module dictionary
    is registered on the multimethod 'name' of StdObjSpace.
    If the name doesn't exist then the alternative namespace is tried
    for registration. 
    """
    from pypy.objspace.std.objspace import StdObjSpace, W_ANY
    namespaces = [StdObjSpace]
    if alt_ns:
        namespaces.insert(0, alt_ns)

    for name, obj in module_dict.items():
        if name.find('__')<1:
            continue
        funcname, sig = name.split('__')
        l=[]
        for i in sig.split('_'):
            if i == 'ANY':
                icls = W_ANY
            else:
                icls = (module_dict.get('W_%s' % i) or
                        module_dict.get('W_%sObject' % i))
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
        if hasattr(ns, funcname):
            return getattr(ns, funcname)
    import typetype
    try:
        return getattr(typetype.W_TypeType, funcname)
    except AttributeError:
        pass  # catches not only the getattr() but the typetype.W_TypeType
              # in case it is not fully imported yet :-((((
    import objecttype
    try:
        return getattr(objecttype.W_ObjectType, funcname)
    except AttributeError:
        pass  # same comment
    raise NameError, ("trying hard but not finding a multimethod named %s" %
                      funcname)

class Curry:
    def __init__(self, fun, arg):
        self.fun = fun
        self.pending = (arg,)

    def __call__(self, *args):
        return self.fun(*(self.pending + args))

def inverted_comparison(function, space, w_1, w_2):
    return space.not_(function(space, w_1, w_2))

def add_extra_comparisons():
    """
    If the module has defined eq, lt or gt,
    check if it already has ne, ge and le respectively.
    If not, then add them as space.not_ on the implemented methods.
    """
    return
    #XXX disabled because it doesn't work correctly probably
    #    because it iterates over partially initialized method tables
    #    we also had discussions on the LLN sprint to implement
    #    a < b with b > a and so on. I wonder whether the automatic
    #    creation of boolean operators is really worth it. instead
    #    we could just implement the operators in their appropriate
    #    files
    operators=(('eq', 'ne'), ('lt', 'ge'), ('gt', 'le'))

    from pypy.objspace.std.objspace import StdObjSpace, W_ANY

    for method, mirror in operators:
        try:
            multifunc = StdObjSpace.__dict__[method]
            mirrorfunc = StdObjSpace.__dict__[mirror]
            for types, functions in multifunc.dispatch_table.iteritems():
                t1, t2 = types
                if t1 is t2:
                    if not mirrorfunc.dispatch_table.has_key(types):
                        assert len(functions) == 1, 'Automatic'
                        'registration of comparison functions'
                        ' only work when there is a single method for'
                        ' the operation.'
                        mirrorfunc.register(
                            Curry(inverted_comparison, functions[0]),
                            *[t1, t1])
        except AttributeError:
            print '%s not found in StdObjSpace' % method
