
def __getattribute__(w_obj,w_name):
  name = space.unwrap(w_name)
  w_descr = space.lookup(w_obj, name)
  if w_descr is not None:
     if space.is_data_descr(w_descr):
         return space.get(w_descr,w_obj,space.type(w_obj))
  w_dict = space.getdict(w_obj)
  if w_dict is not None:
     try:
       return space.getitem(w_dict,w_name)
     except OperationError, e:
       if not e.match(space,space.w_KeyError):
         raise
  if w_descr is not None:
     return space.get(w_descr,w_obj,space.wrap(type))
  raise OperationError(space.w_AttributeError,w_name)

def space.getattr(w_obj,w_name):
   w_descr = space.lookup(w_obj, '__getattribute__')
   try:
     return space.get_and_call_function(w_descr, w_obj, w_name)
   except: # AttributeError
     w_descr = space.lookup(w_obj, '__getattr__')
     if w_descr is None:
       raise
     return space.get_and_call_function(w_descr, w_obj, w_name)

def space.get(w_obj,w_name):
   w_descr = space.lookup(w_obj, '__get__')
   if w_descr is not None:
     return space.get_and_call(w_descr, w_obj, space.newtuple([w_name]))
   else:
     return w_obj

def space.call(w_obj, w_args, w_kwargs):
   w_descr = space.lookup(w_obj, '__call__')
   if w_descr is None:
     raise OperationError(space.w_TypeError, space.wrap('...'))
   return space.get_and_call(w_descr, w_obj, w_args, w_kwargs)


class BaseObjSpace:
  def get_and_call(self, w_descr, w_obj, w_args, w_kwargs):
    if isinstance(w_descr, W_Function):
      args_w = space.unpacktuple(w_args)
      return w_descr.func.call(space.newtuple([w_obj]+args_w),w_kwargs)
    else:
      w_bound = space.get(w_descr,w_obj,space.gettype(w_obj))
      return space.call(w_bound, w_args, w_kwargs)

class Wrappable:
    def __wrap__(self, space):
        return self

class Function(Wrappable):
    TypeDef = Type("function", [], {
        '__call__' : app_descr_function_call,
        'func_code' : Property(func_code_getter) 
        })

class BuiltinType:
    def __init__(self, name, bases, rawdict):
        self.name = name 
        self.bases = bases 
        self.rawdict = rawdict
        self.mro = []

class W_Function:
    def __init__(self, space, func):
        self.func = func
        self.space = space

    def gettype(self):
        space = self.space
        try:
            return space.FunctionType 
        except AttributeError:
            space.FunctionType = f = Type(space, [space.ObjectType]) 
            f.dict_w['__call__'] = space.wrap(app_descr_function_call)
            func_code_property = Property(func_code_getter)
            f.dict_w['func_code'] = space.wrap(func_code_property) 
            return f 

class StdObjectSpace:
    def lookup(space, w_obj, name):
        typ = space._gettype(w_obj)
        return space.wrap(typ.lookup(name))

    def type(space,w_obj):
        return space.wrap(space._gettype(w_obj))

    def _gettype
        try:
            return space._types[w_obj.__class__]
        except KeyError:
            typ = space.buildtype(w_obj.TypeDef) 
            space._types[w_obj.__class__] = typ
            return typ

    def buildtype(space, typedef):
        typ = Type(w_
        for name, value 

    def wrap(space, obj):
        
        assert self.space == space 
        return W_Type(space, self)

def trivspace.lookup(space, w_obj, name):
    if isinstance(w_obj, Wrappable):
        for basedef in w_obj.TypeDef.mro():
            if name in basedef.rawdict:
                return space.wrap(basedef.rawdict[name])
        return None 
    else:
        for cls in w_obj.__class__.__mro__:
            if name in cls.__dict__:
                return cls.__dict__[name]
        return None


def func_code_getter(space,w_func):
    return space.wrap(w_func.func.code)

def object___class__(space,w_obj):
    return space.type(w_obj)

def descr_function_call(space, w_func, w_args, w_kwds): 
    return w_func.func.call(w_args, w_kwds)
app_descr_function_call = gateway.interp2app(descr_function_call) 




class Property:
    def __init__(self, fget, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        self.doc = doc
    def __wrap__(self, space):
        return W_Property(space, self)

class W_Property(...Wrapped):
    def __init__(self, space, property):
        self.space = space
        self.property = property
    def gettype(self):
        space = self.space
        try:
            return space.PropertyType
        except AttributeError:
            space.PropertyType = t = Type(space, "builtin-property", [])
            t.dict_w["__get__"] = space.wrap(app_descr_property_get)
            return t

def descr_property_get(space, w_property, w_obj, w_ignored):
    return w_property.property.fget(space, w_obj)

app_descr_property_get = gateway.interp2app(descr_property_get)


