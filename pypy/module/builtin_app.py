# XXX kwds yet to come

# Problem: need to decide how to implement iterators,
# which are needed for star args.

def apply(function, args):#, kwds):
    return function(*args)#, **kwds)

def map(function, list):
    "docstring"
    return [function(x) for x in list]

def filter(function, list):
    pass

def zip(function, list):
    pass

def reduce(function, list, initial = None):
    if initial is None:
       try:
          initial = list.pop(0)
       except IndexError:
          raise TypeError, "reduce() of empty sequence with no initial value"
    for value in list:
       initial = function(initial, value)
    return initial
    
def isinstance(obj, klass_or_tuple):
    objcls = obj.__class__
    if type(klass_or_tuple) is tuple:
       for klass in klass_or_tuple:
           if issubclass(objcls, klass):
              return 1
       return 0
    else:
       try:
          return issubclass(objcls, klass_or_tuple)
       except TypeError:
          raise TypeError, "isinstance() arg 2 must be a class or type"
 
