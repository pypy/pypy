from pypy.interpreter import eval, function, gateway
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import TypeDef, GetSetProperty, Member
from pypy.objspace.std.model import MultiMethod, FailedToImplement

__all__ = ['StdTypeDef', 'newmethod', 'gateway',
           'GetSetProperty', 'Member', 'attrproperty', 'attrproperty_w',
           'MultiMethod']


class StdTypeDef(TypeDef):

    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only."
        TypeDef.__init__(self, __name, __base, **rawdict)
        self.local_multimethods = []

    def registermethods(self, namespace):
        "NOT_RPYTHON: initialization-time only."
        self.local_multimethods += hack_out_multimethods(namespace)

def issubtypedef(a, b):
    from pypy.objspace.std.objecttype import object_typedef
    if b is object_typedef:
        return True
    while a is not b:
        if a is None:
            return False
        a = a.base
    return True

def attrproperty(name):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, w_obj):
        return space.wrap(getattr(w_obj, name))
    return GetSetProperty(fget)

def attrproperty_w(name):
    "NOT_RPYTHON: initialization-time only"
    def fget(space, w_obj):
        w_value = getattr(w_obj, name)
        if w_value is None:
            return space.w_None
        else:
            return w_value 
    return GetSetProperty(fget)

def descr_get_dict(space, w_obj):
    w_dict = w_obj.getdict()
    assert w_dict is not None, repr(w_obj)
    return w_dict

def descr_set_dict(space, w_obj, w_dict):
    w_obj.setdict(w_dict)

std_dict_descr = GetSetProperty(descr_get_dict, descr_set_dict)

def newmethod(descr_new):
    "NOT_RPYTHON: initialization-time only."
    # this is turned into a static method by the constructor of W_TypeObject.
    return gateway.interp2app(descr_new)

# ____________________________________________________________
#
# All the code below fishes from the multimethod registration tables
# the descriptors to put into the W_TypeObjects.
#

def buildtypeobject(typedef, space):
    "NOT_RPYTHON: initialization-time only."
    # build a W_TypeObject from this StdTypeDef
    from pypy.objspace.std.typeobject import W_TypeObject
    from pypy.objspace.std.objecttype import object_typedef

    w = space.wrap
    rawdict = typedef.rawdict.copy()

    if isinstance(typedef, StdTypeDef):
        # get all the sliced multimethods
        multimethods = slicemultimethods(space, typedef)
        for name, gateway in multimethods.items():
            assert name not in rawdict, 'name clash: %s in %s_typedef' % (
                name, typedef.name)
            rawdict[name] = gateway

    # compute the bases
    if typedef is object_typedef:
        bases_w = []
    else:
        base = typedef.base or object_typedef
        bases_w = [space.gettypeobject(base)]

    # wrap everything
    dict_w = {}
    for descrname, descrvalue in rawdict.items():
        dict_w[descrname] = w(descrvalue)

    return W_TypeObject(space, typedef.name, bases_w, dict_w,
                        overridetypedef=typedef)

def hack_out_multimethods(ns):
    "NOT_RPYTHON: initialization-time only."
    result = []
    for value in ns.itervalues():
        if isinstance(value, MultiMethod):
            result.append(value)
    return result

##def make_frameclass_for_arity(arity, varargs, keywords, isspecial):
##    argnames = []
##    for i in range(arity):
##        argnames.append('arg%dof%d'%(i+1, arity))
##    if varargs:
##        argnames.append('var_args')
##    if keywords:
##        argnames.append('kw_args')
##    self_args_assigning = []
##    for i in range(len(argnames)):
##        self_args_assigning.append('        self.%s = args[%i]'%(argnames[i], i))
##    self_args_assigning = "\n".join(self_args_assigning)
##    self_args = ", ".join(['self.'+ a for a in argnames])
##    name = 'MmFrameOfArity%d'%arity
##    if varargs:
##        name += "Var"
##    if keywords:
##        name += "KW"
##    if isspecial:
##        name = "Special" + name
##    d = locals()
##    template = mmtemplate
##    if isspecial:
##        template += specialmmruntemplate
##    else:
##        template += mmruntemplate
###    print template%d
##    exec template%d in globals(), d
##    return d[name]
##
##_frameclass_for_arity_cache = {}
##def frameclass_for_arity(arity, varargs, keywords, isspecial):
##    try:
##        return _frameclass_for_arity_cache[(arity, varargs, keywords, isspecial)]
##    except KeyError:
##        r = _frameclass_for_arity_cache[(arity, varargs, keywords, isspecial)] = \
##                make_frameclass_for_arity(arity, varargs, keywords, isspecial)
##        return r


def sliced_typeorders(typeorder, multimethod, typedef, i, local=False):
    list_of_typeorders = [typeorder] * multimethod.arity
    prefix = '_mm_' + multimethod.name
    if not local:
        # slice
        sliced_typeorder = {}
        for type, order in typeorder.items():
            thistypedef = getattr(type, 'typedef', None)
            if issubtypedef(thistypedef, typedef):
                lst = []
                for target_type, conversion in order:
                    targettypedef = getattr(target_type, 'typedef', None)
                    if targettypedef == typedef:
                        lst.append((target_type, conversion))
                sliced_typeorder[type] = lst
        list_of_typeorders[i] = sliced_typeorder
        prefix += '_%sS%d' % (typedef.name, i)
    else:
        prefix = typedef.name +'_mth'+prefix
    return prefix, list_of_typeorders

def typeerrormsg(space, operatorsymbol, args_w):
    type_names = [ space.type(w_arg).name for w_arg in args_w ]
    if len(args_w) > 1:
        plural = 's'
    else:
        plural = ''
    msg = "unsupported operand type%s for %s (%s)" % (
                    plural, operatorsymbol,
                    ', '.join(type_names))    
    return space.wrap(msg)

def make_perform_trampoline(prefix, exprargs, expr, miniglobals,  multimethod, selfindex=0,
                            allow_NotImplemented_results=False):
    # mess to figure out how to put a gateway around executing expr
    argnames = ['_%d'%(i+1) for i in range(multimethod.arity)]
    explicit_argnames = multimethod.extras.get('argnames', [])
    argnames[len(argnames)-len(explicit_argnames):] = explicit_argnames
    solid_arglist = ['w_'+name for name in argnames]
    wrapper_arglist = solid_arglist[:]
    if multimethod.extras.get('varargs_w', False):
        wrapper_arglist.append('args_w')
    if multimethod.extras.get('w_varargs', False):
        wrapper_arglist.append('w_args')        
    if multimethod.extras.get('keywords', False):
        raise Exception, "no longer supported, use __args__"
    if multimethod.extras.get('general__args__', False):
        wrapper_arglist.append('__args__')

    miniglobals.update({ 'OperationError': OperationError,                         
                         'typeerrormsg': typeerrormsg})
    
    app_defaults = multimethod.extras.get('defaults', ())
    i = len(argnames) - len(app_defaults)
    wrapper_signature = wrapper_arglist[:]
    for app_default in app_defaults:
        name = wrapper_signature[i]
        wrapper_signature[i] = '%s=%s' % (name, name)
        miniglobals[name] = app_default
        i += 1

    wrapper_signature.insert(0, wrapper_signature.pop(selfindex))
    wrapper_sig  = ', '.join(wrapper_signature)

    src = []
    dest = []
    for wrapper_arg,expr_arg in zip(['space']+wrapper_arglist, exprargs):
        if wrapper_arg != expr_arg:
            src.append(wrapper_arg)
            dest.append(expr_arg)
    renaming = ', '.join(dest) +" = "+', '.join(src)

    if allow_NotImplemented_results and len(multimethod.specialnames) > 1:
        # turn FailedToImplement into NotImplemented
        code = """def %s_perform_call(space, %s):
                      %s
                      try:
                          return %s
                      except FailedToImplement, e:
                          if e.args:
                              raise OperationError(e.args[0], e.args[1])
                          else:
                              return space.w_NotImplemented
"""        % (prefix, wrapper_sig, renaming, expr)
    else:
        # turn FailedToImplement into nice TypeErrors
        code = """def %s_perform_call(space, %s):
                      %s
                      try:
                          w_res = %s
                      except FailedToImplement, e:
                          if e.args:
                              raise OperationError(e.args[0], e.args[1])
                          else:
                              raise OperationError(space.w_TypeError,
                                  typeerrormsg(space, %r, [%s]))
                      if w_res is None:
                          w_res = space.w_None
                      return w_res
"""        % (prefix, wrapper_sig, renaming, expr,
              multimethod.operatorsymbol, ', '.join(solid_arglist))
    exec code in miniglobals
    return miniglobals["%s_perform_call" % prefix]

def wrap_trampoline_in_gateway(func, methname, multimethod):
    unwrap_spec = [gateway.ObjSpace] + [gateway.W_Root]*multimethod.arity
    if multimethod.extras.get('varargs_w', False):
        unwrap_spec.append('args_w')
    if multimethod.extras.get('w_varargs', False):
        unwrap_spec.append('w_args')        
    if multimethod.extras.get('general__args__', False):
        unwrap_spec.append(gateway.Arguments)
    return gateway.interp2app(func, app_name=methname, unwrap_spec=unwrap_spec)

def slicemultimethod(space, multimethod, typedef, result, local=False):
    from pypy.objspace.std.objecttype import object_typedef
    for i in range(len(multimethod.specialnames)):
        # each MultimethodCode embeds a multimethod
        methname = multimethod.specialnames[i]
        if methname in result:
            # conflict between e.g. __lt__ and
            # __lt__-as-reversed-version-of-__gt__
            gw = result[methname]
            if gw.bound_position < i:
                continue

        prefix, list_of_typeorders = sliced_typeorders(
            space.model.typeorder, multimethod, typedef, i, local=local)
        exprargs, expr, miniglobals, fallback = multimethod.install(prefix, list_of_typeorders,
                                                                    baked_perform_call=False)
        if fallback:
            continue   # skip empty multimethods
        trampoline = make_perform_trampoline(prefix, exprargs, expr, miniglobals,
                                             multimethod, i,
                                             allow_NotImplemented_results=True)
        gw = wrap_trampoline_in_gateway(trampoline, methname, multimethod)
        gw.bound_position = i   # for the check above
        result[methname] = gw

def slicemultimethods(space, typedef):
    result = {}
    # import and slice all multimethods of the space.MM container
    for multimethod in hack_out_multimethods(space.MM.__dict__):
        slicemultimethod(space, multimethod, typedef, result)
    # import all multimethods defined directly on the type without slicing
    for multimethod in typedef.local_multimethods:
        slicemultimethod(space, multimethod, typedef, result, local=True)
    return result

##class MultimethodCode(eval.Code):
##    """A code object that invokes a multimethod."""
    
##    def __init__(self, multimethod, framecls, typeclass, bound_position=0):
##        "NOT_RPYTHON: initialization-time only."
##        eval.Code.__init__(self, multimethod.operatorsymbol)
##        self.basemultimethod = multimethod
##        self.typeclass = typeclass
##        self.bound_position = bound_position
##        self.framecls = framecls
##        argnames = ['_%d'%(i+1) for i in range(multimethod.arity)]
##        explicit_argnames = multimethod.extras.get('argnames', [])
##        argnames[len(argnames)-len(explicit_argnames):] = explicit_argnames
##        varargname = kwargname = None
##        # XXX do something about __call__ and __init__ which still use
##        # XXX packed arguments: w_args, w_kwds instead of *args_w, **kwds_w
##        if multimethod.extras.get('varargs', False):
##            varargname = 'args'
##        if multimethod.extras.get('keywords', False):
##            kwargname = 'keywords'
##        self.sig = argnames, varargname, kwargname

##    def computeslice(self, space):
##        "NOT_RPYTHON: initialization-time only."
##        self.mm = self.basemultimethod.__get__(space, slice=(
##            self.typeclass, self.bound_position))
##        return not self.mm.is_empty()

##    def signature(self):
##        return self.sig

##    def getdefaults(self, space):
##        return [space.wrap(x)
##                for x in self.basemultimethod.extras.get('defaults', ())]

##    def create_frame(self, space, w_globals, closure=None):
##        return self.framecls(space, self)

##mmtemplate = """
##class %(name)s(eval.Frame):

##    def setfastscope(self, scope_w):
##        args = list(scope_w)
##        args.insert(0, args.pop(self.code.bound_position))
##%(self_args_assigning)s

##    def getfastscope(self):
##        raise OperationError(self.space.w_TypeError,
##          self.space.wrap("cannot get fastscope of a MmFrame"))
##"""

##mmruntemplate = """
##    def run(self):
##        "Call the multimethod, raising a TypeError if not implemented."
##        w_result = self.code.mm(%(self_args)s)
##        # we accept a real None from operations with no return value
##        if w_result is None:
##            w_result = self.space.w_None
##        return w_result
##"""

##specialmmruntemplate = """

##    def run(self):
##        "Call the multimethods, possibly returning a NotImplemented."
##        try:
##            return self.code.mm.perform_call(%(self_args)s)
##        except FailedToImplement, e:
##            if e.args:
##                raise OperationError(e.args[0], e.args[1])
##            else:
##                return self.space.w_NotImplemented

##"""
