import py
from pypy.interpreter.baseobjspace import Wrappable, W_Root
from pypy.interpreter.argument import Arguments
from pypy.interpreter.error import OperationError
from pypy.interpreter.typedef import GetSetProperty, TypeDef
from pypy.interpreter.gateway import interp2app, ObjSpace
from pypy.rpython.objectmodel import cast_address_to_object, cast_object_to_address
from pypy.rpython.lltypesystem.llmemory import NULL

W_Weakrefable = W_Root
W_Weakrefable.__lifeline__ = None


class WeakrefLifeline(object):
    def __init__(self):
        self.addr_refs = []
        self.w_cached_weakref = None
        self.w_cached_proxy = None
        
    def __del__(self):
        for i in range(len(self.addr_refs) - 1, -1, -1):
            addr_ref = self.addr_refs[i]
            if addr_ref != NULL:
                w_ref = cast_address_to_object(addr_ref, W_Weakref)
                w_ref.invalidate()
        for i in range(len(self.addr_refs) - 1, -1, -1):
            addr_ref = self.addr_refs[i]
            if addr_ref != NULL:
                w_ref = cast_address_to_object(addr_ref, W_Weakref)
                w_ref.activate_callback()
    
    def get_weakref(self, space, w_subtype, w_obj, w_callable):
        w_weakreftype = space.gettypeobject(W_Weakref.typedef)
        is_weakreftype = space.is_w(w_weakreftype, w_subtype)
        can_reuse = space.is_w(w_callable, space.w_None)
        if is_weakreftype and can_reuse and self.w_cached_weakref is not None:
            return self.w_cached_weakref
        w_ref = space.allocate_instance(W_Weakref, w_subtype)
        index = len(self.addr_refs)
        W_Weakref.__init__(w_ref, space, self, index,
                           w_obj, w_callable)
        self.addr_refs.append(cast_object_to_address(w_ref))
        if is_weakreftype and can_reuse:
            self.w_cached_weakref = w_ref
        return w_ref

    def get_proxy(self, space, w_obj, w_callable):
        can_reuse = space.is_w(w_callable, space.w_None)
        if can_reuse and self.w_cached_proxy is not None:
            return self.w_cached_proxy
        index = len(self.addr_refs)
        if space.is_true(space.callable(w_obj)):
            w_proxy = W_CallableProxy(space, self, index, w_obj, w_callable)
        else:
            w_proxy = W_Proxy(space, self, index, w_obj, w_callable)
        self.addr_refs.append(cast_object_to_address(w_proxy))
        if can_reuse:
            self.w_cached_proxy = w_proxy
        return w_proxy

    def ref_is_dead(self, index):
        self.addr_refs[index] = NULL


class W_Weakref(Wrappable):
    def __init__(w_self, space, lifeline, index, w_obj, w_callable):
        w_self.space = space
        w_self.address = cast_object_to_address(w_obj)
        w_self.w_callable = w_callable
        w_self.addr_lifeline = cast_object_to_address(lifeline)
        w_self.index = index

    def dereference(self):
        return cast_address_to_object(self.address, W_Weakrefable)
        
    def invalidate(w_self):
        w_self.address = NULL

    def activate_callback(w_self):
        if not w_self.space.is_w(w_self.w_callable, w_self.space.w_None):
            try:
                w_self.space.call_function(w_self.w_callable, w_self)
            except OperationError, e:
                e.write_unraisable(w_self.space, 'function', w_self.w_callable)

    def __del__(w_self):
        if w_self.address != NULL:
            lifeline = cast_address_to_object(w_self.addr_lifeline,
                                              WeakrefLifeline)
            lifeline.ref_is_dead(w_self.index)


def descr__new__weakref(space, w_subtype, w_obj, w_callable=None):
    assert isinstance(w_obj, W_Weakrefable)
    if w_obj.__lifeline__ is None:
        w_obj.__lifeline__ = WeakrefLifeline()
    return w_obj.__lifeline__.get_weakref(space, w_subtype, w_obj, w_callable)

def descr__eq__(space, ref1, ref2):
    if ref1.address == NULL or ref2.address == NULL:
        return space.is_(ref1, ref2)
    return space.eq(ref1.dereference(), ref2.dereference())

def descr__ne__(space, ref1, ref2):
    return space.not_(space.eq(ref1, ref2))

W_Weakref.typedef = TypeDef("weakref",
    __new__ = interp2app(descr__new__weakref),
    __eq__ = interp2app(descr__eq__,
                        unwrap_spec=[ObjSpace, W_Weakref, W_Weakref]),
    __ne__ = interp2app(descr__ne__,
                        unwrap_spec=[ObjSpace, W_Weakref, W_Weakref]),
    __call__ = interp2app(W_Weakref.dereference, unwrap_spec=['self'])
)


def getweakrefcount(space, w_obj):
    if not isinstance(w_obj, W_Weakrefable):
        return space.wrap(0)
    if w_obj.__lifeline__ is None:
        return space.wrap(0)
    else:
        lifeline = w_obj.__lifeline__
        result = 0
        for i in range(len(lifeline.addr_refs)):
            if lifeline.addr_refs[i] != NULL:
                result += 1
        return space.wrap(result)

def getweakrefs(space, w_obj):
    if not isinstance(w_obj, W_Weakrefable):
        return space.newlist([])
    if w_obj.__lifeline__ is None:
        return space.newlist([])
    else:
        lifeline = w_obj.__lifeline__
        result = []
        for i in range(len(lifeline.addr_refs)):
            addr = lifeline.addr_refs[i]
            if addr != NULL:
                result.append(cast_address_to_object(addr, W_Weakref))
        return space.newlist(result)

#_________________________________________________________________
# Proxy

class W_Proxy(W_Weakref):
    pass

class W_CallableProxy(W_Proxy):
    def descr__call__(self, space, __args__):
        w_obj = force(space, self)
        return space.call_args(w_obj, __args__)

def proxy(space, w_obj, w_callable=None):
    assert isinstance(w_obj, W_Weakrefable)
    if w_obj.__lifeline__ is None:
        w_obj.__lifeline__ = WeakrefLifeline()
    return w_obj.__lifeline__.get_proxy(space, w_obj, w_callable)

def descr__new__proxy(space, w_subtype, w_obj, w_callable=None):
    assert isinstance(w_obj, W_Weakrefable)
    if w_obj.__lifeline__ is None:
        w_obj.__lifeline__ = WeakrefLifeline()
    return w_obj.__lifeline__.get_proxy(space, w_subtype, w_obj, w_callable)

def force(space, proxy):
    if not isinstance(proxy, W_Proxy):
        return proxy
    w_obj = proxy.dereference()
    if space.is_w(w_obj, space.w_None):
        raise OperationError(
            space.w_ReferenceError,
            space.wrap("weakly referenced object no longer exists"))
    return w_obj

proxy_typedef_dict = {}
callable_proxy_typedef_dict = {}
special_ops = {'repr': True}

for opname, _, arity, special_methods in ObjSpace.MethodTable:
    if opname in special_ops:
        continue
    nonspaceargs =  ", ".join(["w_obj%s" % i for i in range(arity)])
    code = "def func(space, %s):\n" % (nonspaceargs, )
    for i in range(arity):
        code += "    w_obj%s = force(space, w_obj%s)\n" % (i, i)
    code += "    return space.%s(%s)" % (opname, nonspaceargs)
    exec py.code.Source(code).compile()
    for special_method in special_methods:
        proxy_typedef_dict[special_method] = interp2app(
            func, unwrap_spec=[ObjSpace] + [W_Root] * arity)
        callable_proxy_typedef_dict[special_method] = interp2app(
            func, unwrap_spec=[ObjSpace] + [W_Root] * arity)


W_Proxy.typedef = TypeDef("weakproxy",
    __new__ = interp2app(descr__new__proxy),
    **proxy_typedef_dict)
W_Proxy.typedef.accepable_as_base_class = False

W_CallableProxy.typedef = TypeDef("callableweakproxy",
    __new__ = interp2app(descr__new__proxy),
    __call__ = interp2app(W_CallableProxy.descr__call__,
                          unwrap_spec=['self', ObjSpace, Arguments]), 
    **callable_proxy_typedef_dict)
W_CallableProxy.typedef.accepable_as_base_class = False

