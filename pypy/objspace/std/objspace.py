import pypy.interpreter.appfile
from pypy.interpreter.baseobjspace import *
from multimethod import *

if not isinstance(bool, type):
    booltype = ()
else:
    booltype = bool


class W_Object:
    "Parent base class for wrapped objects."
    delegate_once = {}
    statictype = None
    
    def __init__(w_self, space):
        w_self.space = space

    def get_builtin_impl_class(w_self):
        return w_self.__class__

W_ANY = W_Object  # synonyms for use in .register()
MultiMethod.ASSERT_BASE_TYPE = W_Object


def registerimplementation(implcls):
    # this function should ultimately register the implementation class somewhere
    # right now its only purpose is to make sure there is a
    # delegate_once attribute.
    implcls.__dict__.setdefault("delegate_once", {})


##################################################################

class StdObjSpace(ObjSpace):
    """The standard object space, implementing a general-purpose object
    library in Restricted Python."""

    PACKAGE_PATH = 'objspace.std'

    class AppFile(pypy.interpreter.appfile.AppFile):
        pass
    AppFile.LOCAL_PATH = [PACKAGE_PATH]


    def standard_types(self):
        class result:
            "Import here the types you want to have appear in __builtin__."

            from objecttype import W_ObjectType
            from booltype   import W_BoolType
            from inttype    import W_IntType
            from floattype  import W_FloatType
            from tupletype  import W_TupleType
            from listtype   import W_ListType
            from dicttype   import W_DictType
            from stringtype import W_StringType
            from typetype   import W_TypeType
            from slicetype  import W_SliceType
        return [value for key, value in result.__dict__.items()
                      if not key.startswith('_')]   # don't look

    def clone_exception_heirachy(self):
        from usertype import W_UserType
        from funcobject import W_FuncObject
        from pypy.interpreter.pycode import PyByteCode
        w = self.wrap
        def __init__(self, *args):
            self.args = args
        code = PyByteCode()
        code._from_code(__init__.func_code)
        w_init = W_FuncObject(self, code,
                              self.newdict([]), self.newtuple([]), None)
##        w_init = w(__init__) # should this work? --mwh
        def __str__(self):
            l = len(self.args)
            if l == 0:
                return ''
            elif l == 1:
                return str(self.args[0])
            else:
                return str(self.args)
        code = PyByteCode()
        code._from_code(__str__.func_code)
        w_str = W_FuncObject(self, code,
                              self.newdict([]), self.newtuple([]), None)
        import exceptions

        # to create types, we should call the standard type object;
        # but being able to do that depends on the existence of some
        # of the exceptions...
        
        self.w_Exception = W_UserType(
            self,
            w('Exception'),
            self.newtuple([]),
            self.newdict([(w('__init__'), w_init),
                          (w('__str__'), w_str)]))
        self.w_IndexError = self.w_Exception
        
        done = {'Exception': self.w_Exception}

        # some of the complexity of the following is due to the fact
        # that we need to create the tree root first, but the only
        # connections we have go in the inconvenient direction...
        
        for k in dir(exceptions):
            if k not in done:
                v = getattr(exceptions, k)
                if isinstance(v, str):
                    continue
                stack = [k]
                while stack:
                    next = stack[-1]
                    if next not in done:
                        v = getattr(exceptions, next)
                        b = v.__bases__[0]
                        if b.__name__ not in done:
                            stack.append(b.__name__)
                            continue
                        else:
                            base = done[b.__name__]
                            newtype = self.call_function(
                                self.w_type,
                                w(k),
                                self.newtuple([base]),
                                self.newdict([]))
                            setattr(self,
                                    'w_' + next,
                                    newtype)
                            done[next] = newtype
                            stack.pop()
                    else:
                        stack.pop()
        return done
                            
    def initialize(self):
        from noneobject    import W_NoneObject
        from boolobject    import W_BoolObject
        from cpythonobject import W_CPythonObject

        # singletons
        self.w_None  = W_NoneObject(self)
        self.w_False = W_BoolObject(self, False)
        self.w_True  = W_BoolObject(self, True)
        self.w_NotImplemented = self.wrap(NotImplemented)  # XXX do me

        for_builtins = {"False": self.w_False,
                        "True" : self.w_True,
                        "None" : self.w_None,
                        "NotImplemented": self.w_NotImplemented,
                        }

        # types
        self.types_w = {}
        for typeclass in self.standard_types():
            w_type = self.get_typeinstance(typeclass)
            setattr(self, 'w_' + typeclass.typename, w_type)
            for_builtins[typeclass.typename] = w_type

        # exceptions
        for_builtins.update(self.clone_exception_heirachy())
        
        self.make_builtins()
        self.make_sys()
        
        # insert stuff into the newly-made builtins
        for key, w_value in for_builtins.items():
            self.setitem(self.w_builtins, self.wrap(key), w_value)

    def get_typeinstance(self, typeclass):
        assert typeclass.typename is not None, (
            "get_typeinstance() cannot be used for %r" % typeclass)
        # types_w maps each W_XxxType class to its unique-for-this-space instance
        try:
            w_type = self.types_w[typeclass]
        except:
            w_type = self.types_w[typeclass] = typeclass(self)
        return w_type

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

    getdict = MultiMethod('getdict', 1, [])  # get '.__dict__' attribute


# add all regular multimethods to StdObjSpace
for _name, _symbol, _arity, _specialnames in ObjSpace.MethodTable:
    setattr(StdObjSpace, _name, MultiMethod(_symbol, _arity, _specialnames))

# import the common base W_ObjectObject as well as
# default implementations of some multimethods for all objects
# that don't explicitely override them or that raise FailedToImplement
import pypy.objspace.std.objectobject
import pypy.objspace.std.default
