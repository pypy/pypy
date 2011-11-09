from pypy.interpreter import gateway, baseobjspace, argument
from pypy.interpreter.error import OperationError, operationerrfmt
from pypy.interpreter.typedef import TypeDef, GetSetProperty, Member
from pypy.interpreter.typedef import descr_get_dict, descr_set_dict
from pypy.interpreter.typedef import descr_del_dict
from pypy.interpreter.baseobjspace import SpaceCache
from pypy.objspace.std import model
from pypy.objspace.std.model import StdObjSpaceMultiMethod
from pypy.objspace.std.multimethod import FailedToImplement
from pypy.rlib import jit
from pypy.tool.sourcetools import compile2

__all__ = ['StdTypeDef', 'SMM']

SMM = StdObjSpaceMultiMethod


class StdTypeDef(TypeDef):

    def __init__(self, __name, __base=None, **rawdict):
        "NOT_RPYTHON: initialization-time only."
        TypeDef.__init__(self, __name, __base, **rawdict)
        self.any = type("W_Any"+__name.title(), (baseobjspace.W_Root,), {'typedef': self})
        self.local_multimethods = []

    def registermethods(self, namespace):
        "NOT_RPYTHON: initialization-time only."
        self.local_multimethods += hack_out_multimethods(namespace)

@jit.unroll_safe
def issubtypedef(a, b):
    from pypy.objspace.std.objecttype import object_typedef
    if b is object_typedef:
        return True
    if a is None:
        return False
    if a is b:
        return True
    for a1 in a.bases:
        if issubtypedef(a1, b):
            return True
    return False

std_dict_descr = GetSetProperty(descr_get_dict, descr_set_dict, descr_del_dict,
                    doc="dictionary for instance variables (if defined)")
std_dict_descr.name = '__dict__'

# ____________________________________________________________
#
# All the code below fishes from the multimethod registration tables
# the descriptors to put into the W_TypeObjects.
#

class TypeCache(SpaceCache):
    def build(cache, typedef):
        "NOT_RPYTHON: initialization-time only."
        # build a W_TypeObject from this StdTypeDef
        from pypy.objspace.std.typeobject import W_TypeObject
        from pypy.objspace.std.objecttype import object_typedef

        space = cache.space
        w = space.wrap
        rawdict = typedef.rawdict
        lazyloaders = {}

        if isinstance(typedef, StdTypeDef):
            # get all the sliced multimethods
            multimethods = slicemultimethods(space, typedef)
            for name, loader in multimethods.items():
                if name in rawdict:
                    # the name specified in the rawdict has priority
                    continue
                assert name not in lazyloaders, (
                    'name clash: %s in %s.lazyloaders' % (name, typedef.name))
                lazyloaders[name] = loader

        # compute the bases
        if typedef is object_typedef:
            bases_w = []
        else:
            bases = typedef.bases or [object_typedef]
            bases_w = [space.gettypeobject(base) for base in bases]

        # wrap everything
        dict_w = {}
        for descrname, descrvalue in rawdict.items():
            dict_w[descrname] = w(descrvalue)

        if typedef.applevel_subclasses_base is not None:
            overridetypedef = typedef.applevel_subclasses_base.typedef
        else:
            overridetypedef = typedef
        w_type = W_TypeObject(space, typedef.name, bases_w, dict_w,
                              overridetypedef=overridetypedef)
        if typedef is not overridetypedef:
            w_type.w_doc = space.wrap(typedef.doc)
        w_type.lazyloaders = lazyloaders
        return w_type

    def ready(self, w_type):
        w_type.ready()

def hack_out_multimethods(ns):
    "NOT_RPYTHON: initialization-time only."
    result = []
    seen = {}
    for value in ns.itervalues():
        if isinstance(value, StdObjSpaceMultiMethod):
            if value.name in seen:
                raise Exception("duplicate multimethod name %r" %
                                (value.name,))
            seen[value.name] = True
            result.append(value)
    return result

def is_relevant_for_slice(target_type, typedef):
    targettypedef = getattr(target_type, 'typedef', None)
    if targettypedef == typedef:
        return True
    method = getattr(target_type, "is_implementation_for", lambda t: False)
    return method(typedef)

def sliced_typeorders(typeorder, multimethod, typedef, i, local=False):
    """NOT_RPYTHON"""
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
                    if is_relevant_for_slice(target_type, typedef):
                        lst.append((target_type, conversion))
                sliced_typeorder[type] = lst
        list_of_typeorders[i] = sliced_typeorder
        prefix += '_%sS%d' % (typedef.name, i)
    else:
        prefix = typedef.name +'_mth'+prefix
    return prefix, list_of_typeorders

def _gettypeerrormsg(nbargs):
    if nbargs > 1:
        plural = 's'
    else:
        plural = ''
    return "unsupported operand type%s for %%s: %s" % (
        plural, ', '.join(["'%s'"] * nbargs))
_gettypeerrormsg._annspecialcase_ = 'specialize:memo'

def _gettypenames(space, *args_w):
    if args_w:
        typename = space.type(args_w[-1]).getname(space)
        return _gettypenames(space, *args_w[:-1]) + (typename,)
    return ()
_gettypenames._always_inline_ = True

def gettypeerror(space, operatorsymbol, *args_w):
    msg = _gettypeerrormsg(len(args_w))
    type_names = _gettypenames(space, *args_w)
    return operationerrfmt(space.w_TypeError, msg,
                           operatorsymbol, *type_names)

def make_perform_trampoline(prefix, exprargs, expr, miniglobals,  multimethod, selfindex=0,
                            allow_NotImplemented_results=False):
    """NOT_RPYTHON"""    
    # mess to figure out how to put a gateway around executing expr
    argnames = ['_%d'%(i+1) for i in range(multimethod.arity)]
    explicit_argnames = multimethod.extras.get('argnames', [])
    argnames[len(argnames)-len(explicit_argnames):] = explicit_argnames
    solid_arglist = ['w_'+name for name in argnames]
    wrapper_arglist = solid_arglist[:]
    if multimethod.extras.get('varargs_w', False):
        wrapper_arglist.append('args_w')
    if multimethod.extras.get('keywords', False):
        raise Exception, "no longer supported, use __args__"
    if multimethod.extras.get('general__args__', False):
        wrapper_arglist.append('__args__')
    wrapper_arglist += multimethod.extras.get('extra_args', ())

    miniglobals.update({ 'OperationError': OperationError,
                         'gettypeerror': gettypeerror})
    
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

    # add a call to resolve_target to give the thunk space a chance to replace
    # the thing with something else
    offset = len(multimethod.argnames_before)
    renaming += "; %s = space.resolve_target(%s)" % (
            exprargs[selfindex+offset], exprargs[selfindex+offset])

    if allow_NotImplemented_results and (len(multimethod.specialnames) > 1 or
                                         multimethod.name.startswith('inplace_')):
        # turn FailedToImplement into NotImplemented
        code = """def %s_perform_call(space, %s):
                      %s
                      try:
                          return %s
                      except FailedToImplement, e:
                          if e.get_w_type(space) is not None:
                              raise OperationError(e.w_type, e.get_w_value(space))
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
                          if e.get_w_type(space) is not None:
                              raise OperationError(e.w_type, e.get_w_value(space))
                          else:
                              raise gettypeerror(space, %r, %s)
                      if w_res is None:
                          w_res = space.w_None
                      return w_res
"""        % (prefix, wrapper_sig, renaming, expr,
              multimethod.operatorsymbol, ', '.join(solid_arglist))
    exec compile2(code, '', 'exec') in miniglobals 
    return miniglobals["%s_perform_call" % prefix]

def wrap_trampoline_in_gateway(func, methname, multimethod):
    """NOT_RPYTHON"""
    if 'doc' in multimethod.extras:
        func.__doc__ = multimethod.extras['doc']
    return gateway.interp2app(func, app_name=methname)

def slicemultimethod(space, multimethod, typedef, result, local=False):
    """NOT_RPYTHON"""    
    for i in range(len(multimethod.specialnames)):
        methname = multimethod.specialnames[i]
        if methname in result:
            # conflict between e.g. __lt__ and
            # __lt__-as-reversed-version-of-__gt__
            loader = result[methname]
            if loader.bound_position < i:
                continue

        def multimethod_loader(i=i, methname=methname):
            """NOT_RPYTHON"""
            prefix, list_of_typeorders = sliced_typeorders(
                space.model.typeorder, multimethod, typedef, i, local=local)
            exprargs, expr, miniglobals, fallback = multimethod.install(prefix, list_of_typeorders,
                                                                        baked_perform_call=False,
                                                                        base_typeorder=space.model.typeorder)
            if fallback:
                return None   # skip empty multimethods
            trampoline = make_perform_trampoline(prefix, exprargs, expr, miniglobals,
                                                 multimethod, i,
                                                 allow_NotImplemented_results=True)
            gw = wrap_trampoline_in_gateway(trampoline, methname, multimethod)
            return space.wrap(gw)

        multimethod_loader.bound_position = i   # for the check above
        result[methname] = multimethod_loader

def slicemultimethods(space, typedef):
    """NOT_RPYTHON"""
    result = {}
    # import and slice all multimethods of the MM container
    for multimethod in hack_out_multimethods(model.MM.__dict__):
        slicemultimethod(space, multimethod, typedef, result)
    # import all multimethods defined directly on the type without slicing
    for multimethod in typedef.local_multimethods:
        slicemultimethod(space, multimethod, typedef, result, local=True)
    return result

def multimethods_defined_on(cls):
    """NOT_RPYTHON: enumerate the (multimethod, local_flag) for all the
    multimethods that have an implementation whose first typed argument
    is 'cls'.
    """
    typedef = cls.typedef
    for multimethod in hack_out_multimethods(model.MM.__dict__):
        if cls in multimethod.dispatch_tree:
            yield multimethod, False
    for multimethod in typedef.local_multimethods:
        yield multimethod, True
