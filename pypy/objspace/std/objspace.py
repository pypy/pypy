import pypy.interpreter.appfile
from pypy.interpreter.baseobjspace import *
from multimethod import *

if not isinstance(bool, type):
    booltype = ()
else:
    booltype = bool


##################################################################

class StdObjSpace(ObjSpace):
    """The standard object space, implementing a general-purpose object
    library in Restricted Python."""

    PACKAGE_PATH = 'objspace.std'

    class AppFile(pypy.interpreter.appfile.AppFile):
        pass
    AppFile.LOCAL_PATH = [PACKAGE_PATH]

    def initialize(self):
        from noneobject    import W_NoneObject
        from boolobject    import W_BoolObject
        from cpythonobject import W_CPythonObject
        self.w_None  = W_NoneObject()
        self.w_False = W_BoolObject(False)
        self.w_True  = W_BoolObject(True)
        # hack in the exception classes
        import __builtin__, types
        newstuff = {"False": self.w_False,
                    "True" : self.w_True,
                    "None" : self.w_None,
                    }
        for n, c in __builtin__.__dict__.iteritems():
            if isinstance(c, types.ClassType) and issubclass(c, Exception):
                w_c = W_CPythonObject(c)
                setattr(self, 'w_' + c.__name__, w_c)
                newstuff[c.__name__] = w_c
        self.make_builtins()
        self.make_sys()
        # insert these into the newly-made builtins
        for key, w_value in newstuff.items():
            self.setitem(self.w_builtins, self.wrap(key), w_value)
        # add a dummy __import__  XXX fixme
#        w_import = self.wrap(__import__)
#        self.setitem(self.w_builtins, self.wrap("__import__"), w_import)

    def wrap(self, x):
        "Wraps the Python value 'x' into one of the wrapper classes."
        if x is None:
            return self.w_None
        if isinstance(x, int):
            if isinstance(x, booltype):
                return self.newbool(x)
            import intobject
            return intobject.W_IntObject(x)
        if isinstance(x, str):
            import stringobject
            return stringobject.W_StringObject(x)
        #if isinstance(x, float):
        #    import floatobject
        #    return floatobject.W_FloatObject(x)
        if isinstance(x, tuple):
            wrappeditems = [self.wrap(item) for item in x]
            import tupleobject
            return tupleobject.W_TupleObject(wrappeditems)
        import cpythonobject
        return cpythonobject.W_CPythonObject(x)

    def newtuple(self, list_w):
        import tupleobject
        return tupleobject.W_TupleObject(list_w)

    def newlist(self, list_w):
        #import listobject
        #return listobject.W_ListObject(list_w)
        return self.wrap([self.unwrap(w_x) for w_x in list_w])

    def newdict(self, list_pairs_w):
        import dictobject
        return dictobject.W_DictObject(list_pairs_w)

    def newslice(self, w_start, w_end, w_step):
        # w_step may be a real None
        import sliceobject
        return sliceobject.W_SliceObject(w_start, w_end, w_step)

    def newfunction(self, code, w_globals, w_defaultarguments, w_closure=None):
        import funcobject
        return funcobject.W_FuncObject(code, w_globals,
                                       w_defaultarguments, w_closure)

    def newmodule(self, w_name):
        import moduleobject
        return moduleobject.W_ModuleObject(self, w_name)

    def newstring(self, chars_w):
        # nyyyaaaaaaaaagh!  what do we do if chars_w is not a list, or
        # if it is a list, but contains things other than wrapped
        # integers -- mwh
        try:
            chars = [chr(self.unwrap(w_c)) for w_c in chars_w]
        except TypeError:   # chr(not-an-integer)
            raise OperationError(self.w_TypeError,
                                 self.wrap("an integer is required"))
        except ValueError:  # chr(out-of-range)
            raise OperationError(self.w_ValueError,
                                 self.wrap("character code not in range(256)"))
        import stringobject
        return stringobject.W_StringObject(''.join(chars))

    # special multimethods
    unwrap  = MultiMethod('unwrap', 1)   # returns an unwrapped object
    is_true = MultiMethod('nonzero', 1)  # returns an unwrapped bool

##    # handling of the common fall-back cases
##    def compare_any_any(self, w_1, w_2, operation):
##        if operation == "is":
##            return self.newbool(w_1 == w_2)
##        elif operation == "is not":
##            return self.newbool(w_1 != w_2)
##        else:
##            raise FailedToImplement(self.w_TypeError,
##                                    "unknown comparison operator %r" % operation)
        
##    compare.register(compare_any_any, W_ANY, W_ANY)


# add all regular multimethods to StdObjSpace
for _name, _symbol, _arity in ObjSpace.MethodTable:
    setattr(StdObjSpace, _name, MultiMethod(_symbol, _arity))

# default implementations of some multimethods for all objects
# that don't explicitely override them or that raise FailedToImplement

def default_eq(space, w_a, w_b):
    return space.is_(w_a, w_b)

StdObjSpace.eq.register(default_eq, W_ANY, W_ANY)

def default_ne(space, w_a, w_b):
    return space.not_(space.is_(w_a, w_b))

StdObjSpace.ne.register(default_ne, W_ANY, W_ANY)

def default_id(space, w_obj):
    import intobject
    return intobject.W_IntObject(id(w_obj))

StdObjSpace.id.register(default_id, W_ANY)

def default_not(space, w_obj):
    return space.newbool(not space.is_true(w_obj))

StdObjSpace.not_.register(default_not, W_ANY)

def default_is_true(space, w_obj):
    return True   # everything is True unless otherwise specified

StdObjSpace.is_true.register(default_is_true, W_ANY)

def default_getattr(space, w_obj, w_attr):
    # XXX build a nicer error message along these lines:
    #w_type = space.type(w_obj)
    #w_typename = space.getattr(w_type, space.wrap('__name__'))
    #...
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.getattr.register(default_getattr, W_ANY, W_ANY)

def default_setattr(space, w_obj, w_attr, w_value):
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.setattr.register(default_getattr, W_ANY, W_ANY, W_ANY)

def default_delattr(space, w_obj, w_attr, w_value):
    raise OperationError(space.w_AttributeError, w_attr)

StdObjSpace.delattr.register(default_getattr, W_ANY, W_ANY)
