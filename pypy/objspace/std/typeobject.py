from pypy.objspace.std.objspace import *


class W_TypeObject(W_Object):
    from pypy.objspace.std.typetype import type_typedef as typedef

    def __init__(w_self, space, name, bases_w, dict_w):
        W_Object.__init__(w_self, space)
        w_self.name = name
        w_self.bases_w = bases_w
        w_self.dict_w = dict_w

    def getmro(w_self):
        # XXX this is something that works not too bad right now
        # XXX do the complete mro thing later (see mro.py)
        mro = [w_self]
        for w_parent in w_self.bases_w:
            mro += w_parent.getmro()
        return mro

    def lookup(w_self, key):
        # note that this doesn't call __get__ on the result at all
        # XXX this should probably also return the (parent) class in which
        # the attribute was found
        space = w_self.space
        for w_class in w_self.getmro():
            try:
                return w_class.dict_w[key]
            except KeyError:
                pass
        return None

##    def lookup_exactly_here(w_self, w_key):
##        space = w_self.space
##        multimethods = getmultimethods(space.__class__, w_self.__class__)
##        key = space.unwrap(w_key)
##        if not isinstance(key, str):
##            raise OperationError(space.w_TypeError,
##                       space.wrap('attribute name must be string'))
##        try:
##            code = multimethods[key]
##        except KeyError:
##            raise KeyError   # pass on the KeyError
##        if code.slice().is_empty():
##            raise KeyError
##        fn = function.Function(space, code, defs_w=code.getdefaults(space))
##        return space.wrap(fn)


##def hack_out_multimethods(cls):
##    result = []
##    for base in cls.__bases__:
##        result += hack_out_multimethods(base)
##    for value in cls.__dict__.itervalues():
##        if isinstance(value, MultiMethod):
##            result.append(value)
##    return result

##AllSlicedMultimethods = {}

##def getmultimethods(spaceclass, typeclass):
##    try:
##        multimethods = AllSlicedMultimethods[spaceclass, typeclass]
##    except KeyError:
##        multimethods = AllSlicedMultimethods[spaceclass, typeclass] = {}
##        # import all multimethods of the type class and of the objspace
##        for multimethod in (hack_out_multimethods(typeclass) +
##                            hack_out_multimethods(spaceclass)):
##            for i in range(len(multimethod.specialnames)):
##                # each MultimethodCode embeds a multimethod
##                name = multimethod.specialnames[i]
##                if name in multimethods:
##                    # conflict between e.g. __lt__ and
##                    # __lt__-as-reversed-version-of-__gt__
##                    code = multimethods[name]
##                    if code.bound_position < i:
##                        continue
##                mmframeclass = multimethod.extras.get('mmframeclass')
##                if mmframeclass is None:
##                    if len(multimethod.specialnames) > 1:
##                        mmframeclass = SpecialMmFrame
##                    else:
##                        mmframeclass = MmFrame
##                code = MultimethodCode(multimethod, mmframeclass, typeclass, i)
##                multimethods[name] = code
##        # add some more multimethods with a special interface
##        code = MultimethodCode(spaceclass.next, NextMmFrame, typeclass)
##        multimethods['next'] = code
##        code = MultimethodCode(spaceclass.is_true, NonZeroMmFrame, typeclass)
##        multimethods['__nonzero__'] = code
##    return multimethods

##class MultimethodCode(eval.Code):
##    """A code object that invokes a multimethod."""
    
##    def __init__(self, multimethod, framecls, typeclass, bound_position=0):
##        eval.Code.__init__(self, multimethod.operatorsymbol)
##        self.basemultimethod = multimethod
##        self.typeclass = typeclass
##        self.bound_position = bound_position
##        self.framecls = framecls
##        argnames = ['x%d'%(i+1) for i in range(multimethod.arity)]
##        argnames.insert(0, argnames.pop(self.bound_position))
##        varargname = kwargname = None
##        if multimethod.extras.get('varargs', False):
##            varargname = 'args'
##        if multimethod.extras.get('keywords', False):
##            kwargname = 'keywords'
##        self.sig = argnames, varargname, kwargname
        
##    def signature(self):
##        return self.sig

##    def getdefaults(self, space):
##        return [space.wrap(x)
##                for x in self.basemultimethod.extras.get('defaults', ())]

##    def slice(self):
##        return self.basemultimethod.slice(self.typeclass, self.bound_position)

##    def create_frame(self, space, w_globals, closure=None):
##        return self.framecls(space, self)

##class MmFrame(eval.Frame):
##    def run(self):
##        "Call the multimethod, raising a TypeError if not implemented."
##        mm = self.code.slice().get(self.space)
##        args = self.fastlocals_w
##        w_result = mm(*args)
##        # we accept a real None from operations with no return value
##        if w_result is None:
##            w_result = self.space.w_None
##        return w_result

##class SpecialMmFrame(eval.Frame):
##    def run(self):
##        "Call the multimethods, possibly returning a NotImplemented."
##        mm = self.code.slice().get(self.space)
##        args = self.fastlocals_w
##        try:
##            return mm.perform_call(args)
##        except FailedToImplement, e:
##            if e.args:
##                raise OperationError(*e.args)
##            else:
##                return self.space.w_NotImplemented

##class NextMmFrame(eval.Frame):
##    def run(self):
##        "Call the next() multimethod."
##        mm = self.code.slice().get(self.space)
##        args = self.fastlocals_w
##        try:
##            return mm(*args)
##        except NoValue:
##            raise OperationError(self.space.w_StopIteration,
##                                 self.space.w_None)

##class NonZeroMmFrame(eval.Frame):
##    def run(self):
##        "Call the is_true() multimethods."
##        mm = self.code.slice().get(self.space)
##        args = self.fastlocals_w
##        result = mm(*args)
##        return self.space.newbool(result)


def call__Type(space, w_type, w_args, w_kwds):
    args_w = space.unpacktuple(w_args)
    # special case for type(x)
    if (space.is_true(space.is_(w_type, space.w_type)) and
        len(args_w) == 1 and not space.is_true(w_kwds)):
        return space.type(args_w[0])
    # invoke the __new__ of the type
    w_descr = w_type.lookup('__new__')
    w_extendedargs = space.newtuple([w_type] + args_w)
    w_newobject = space.call(w_descr, w_extendedargs, w_kwds)
    # maybe invoke the __init__ of the type
    if space.is_true(space.isinstance(w_newobject, w_type)):
        w_descr = space.lookup(w_newobject, '__init__')
        if w_descr is not None:
            space.get_and_call(w_descr, w_newobject, w_args, w_kwds)
    return w_newobject

def issubtype__Type_Type(space, w_type1, w_type2):
    return space.newbool(w_type2 in w_type1.getmro())

def repr__Type(space, w_obj):
    return space.wrap("<pypy type '%s'>" % w_obj.typename)  # XXX remove 'pypy'

def getattr__Type_ANY(space, w_type, w_name):
    name = space.unwrap(w_name)
    w_descr = space.lookup(w_type, name)
    if w_descr is not None:
        if space.is_data_descr(w_descr):
            return space.get(w_descr,w_type,space.type(w_type))
    w_value = w_type.lookup(name)
    if w_value is not None:
        # __get__(None, type): turns e.g. functions into unbound methods
        return space.get(w_value, space.w_None, w_type)
    if w_descr is not None:
        return space.get(w_descr,w_type,space.type(w_type))
    raise OperationError(space.w_AttributeError,w_name)

# XXX __setattr__
# XXX __delattr__
# XXX __hash__ ??


register_all(vars())
