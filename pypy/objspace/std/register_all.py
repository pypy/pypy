
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

        if len(l) != obj.func_code.co_argcount-1:
            raise ValueError, \
                  "function name %s doesn't specify exactly %d arguments" % (
                     repr(name), obj.func_code.co_argcount-1)

        funcname =  _name_mappings.get(funcname, funcname)

        if hasattr(alt_ns, funcname):
            getattr(alt_ns, funcname).register(obj, *l)
        else:
            getattr(StdObjSpace, funcname).register(obj, *l)
    add_extra_comparisons()

class Curry:
    def __init__(self, fun, arg):
        self.fun = fun
        self.pending = [arg]

    def __call__(self, *args):
        return self.fun(*(self.pending + args))

def inverted_comparison(function, space, w_1, w_2):
    return space.not_(function(space, w_1, w_2))

def add_extra_comparisons(
    operators=(('eq', 'ne'), ('lt', 'ge'), ('gt', 'le'))):
    """
    If the module has defined eq, lt or gt,
    check if it already has ne, ge and le respectively.
    If not, then add them as space.not_ on the implemented methods.
    """
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
