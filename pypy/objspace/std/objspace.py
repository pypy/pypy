import pypy.interpreter.appfile
from pypy.interpreter.baseobjspace import *
from multimethod import *

if not isinstance(bool, type):
    booltype = ()
else:
    booltype = bool


class W_Object:
    "Parent base class for wrapped objects."
    statictype = None
    
    def __init__(w_self, space):
        w_self.space = space

    def get_builtin_impl_class(w_self):
        return w_self.__class__


class implmethod(object):
    def __init__(self):
        self.dispatch_table = {}
    def register(self, function, *types):
        if types in self.dispatch_table:
            raise error, "we already got an implementation for %r" % types
        self.dispatch_table[types] = function
        return self
    def __get__(self, instance, cls=None):
        raise "XXX come back later"


##################################################################

class StdObjSpace(ObjSpace):
    """The standard object space, implementing a general-purpose object
    library in Restricted Python."""

    PACKAGE_PATH = 'objspace.std'

    class AppFile(pypy.interpreter.appfile.AppFile):
        pass
    AppFile.LOCAL_PATH = [PACKAGE_PATH]

    BUILTIN_TYPES = {
        'W_NoneObject':  'noneobject',
        'W_BoolObject':  'boolobject',
        'W_IntObject':   'intobject',
        'W_FloatObject': 'floatobject',
        'W_ListObject':  'listobject',
        'W_DictObject':  'dictobject',
        #'W_StringObject': 'stringobject',
        'W_ModuleObject':'moduleobject',
        }

    def initialize(self):
        self.TYPE_CACHE = {}
        from noneobject    import W_NoneObject
        from boolobject    import W_BoolObject
        from cpythonobject import W_CPythonObject
        from typeobject    import W_TypeObject, make_type_by_name
        self.w_None  = W_NoneObject(self)
        self.w_False = W_BoolObject(self, False)
        self.w_True  = W_BoolObject(self, True)
        self.w_NotImplemented = self.wrap(NotImplemented)  # XXX do me
        # hack in the exception classes
        import __builtin__, types
        newstuff = {"False": self.w_False,
                    "True" : self.w_True,
                    "None" : self.w_None,
                    "NotImplemented": self.w_NotImplemented,
                    }
        for n, c in __builtin__.__dict__.iteritems():
            if isinstance(c, types.ClassType) and issubclass(c, Exception):
                w_c = W_CPythonObject(self, c)
                setattr(self, 'w_' + c.__name__, w_c)
                newstuff[c.__name__] = w_c
        # make the types
        for classname, modulename in self.BUILTIN_TYPES.iteritems():
            mod = __import__(modulename, globals(), locals(), [classname])
            cls = getattr(mod, classname)
            w_type = make_type_by_name(self, cls.statictypename)
            w_type.setup_builtin_type(cls)
            setattr(self, 'w_' + cls.statictypename, w_type)
            newstuff[cls.statictypename] = w_type
        
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
        if isinstance(x, W_Object):
            raise TypeError, "attempt to wrap already wrapped object: %s"%(x,)
        if isinstance(x, int):
            if isinstance(x, booltype):
                return self.newbool(x)
            import intobject
            return intobject.W_IntObject(self, x)
        if isinstance(x, str):
            import stringobject
            return stringobject.W_StringObject(self, x)
        if isinstance(x, dict):
            items_w = [(self.wrap(k), self.wrap(v)) for (k, v) in x.iteritems()]
            import dictobject
            return dictobject.W_DictObject(self, items_w)
        if isinstance(x, float):
            import floatobject
            return floatobject.W_FloatObject(self, x)
        if isinstance(x, tuple):
            wrappeditems = [self.wrap(item) for item in x]
            import tupleobject
            return tupleobject.W_TupleObject(self, wrappeditems)
        if isinstance(x, list):
            wrappeditems = [self.wrap(item) for item in x]
            import listobject
            return listobject.W_ListObject(self, wrappeditems)
        import cpythonobject
        return cpythonobject.W_CPythonObject(self, x)

    def newtuple(self, list_w):
        import tupleobject
        return tupleobject.W_TupleObject(self, list_w)

    def newlist(self, list_w):
        import listobject
        return listobject.W_ListObject(self, list_w)

    def newdict(self, list_pairs_w):
        import dictobject
        return dictobject.W_DictObject(self, list_pairs_w)

    def newslice(self, w_start, w_end, w_step):
        # w_step may be a real None
        import sliceobject
        return sliceobject.W_SliceObject(self, w_start, w_end, w_step)

    def newfunction(self, code, w_globals, w_defaultarguments, w_closure=None):
        import funcobject
        return funcobject.W_FuncObject(self, code, w_globals,
                                       w_defaultarguments, w_closure)

    def newmodule(self, w_name):
        import moduleobject
        return moduleobject.W_ModuleObject(self, w_name)

    def newstring(self, chars_w):
        try:
            chars = [chr(self.unwrap(w_c)) for w_c in chars_w]
        except TypeError:   # chr(not-an-integer)
            raise OperationError(self.w_TypeError,
                                 self.wrap("an integer is required"))
        except ValueError:  # chr(out-of-range)
            raise OperationError(self.w_ValueError,
                                 self.wrap("character code not in range(256)"))
        import stringobject
        return stringobject.W_StringObject(self, ''.join(chars))

    # special multimethods
    unwrap  = MultiMethod('unwrap', 1, [])   # returns an unwrapped object
    is_true = MultiMethod('nonzero', 1, [])  # returns an unwrapped bool
    # XXX do something about __nonzero__ !

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
for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    setattr(StdObjSpace, _name, MultiMethod(_symbol, _arity, _specialnames))

# default implementations of some multimethods for all objects
# that don't explicitely override them or that raise FailedToImplement

import pypy.objspace.std.default
