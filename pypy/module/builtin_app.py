import types

# XXX kwds yet to come

# Problem: need to decide how to implement iterators,
# which are needed for star args.

def apply(function, args):#, kwds):
    return function(*args)#, **kwds)

def map(function, list):
    "docstring"
    return [function(x) for x in list]

def isinstance(obj, klass_or_tuple):
    objcls = obj.__class__
    if type(klass_or_tuple) == types.TupleType:
       for klass in klass_or_tuple:
           if issubclass(objcls, klass):
              return 1
       return 0
    elif type(klass_or_tuple) == types.ClassType:
       return issubclass(objcls, klass_or_tuple)
    else:
       raise TypeError, "isinstance() arg 2 must be a class or type"
 
