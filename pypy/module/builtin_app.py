# XXX kwds yet to come

# Problem: need to decide how to implement iterators,
# which are needed for star args.

def apply(function, args, kwds):
    return function(*args, **kwds)

def map(function, *collections):
    if len(collections) == 1:
       #it's the most common case, so make it faster
       return [function(x) for x in collections[0]]
    else:
       res = []
       idx = 0   
       while 1:
          cont = 0     #is any collection not empty?
          args = []
          for collection in collections:
              try:
                 elem = collection[idx]
                 cont = cont + 1
              except IndexError:
                 elem = None
              args.append(elem)
          if cont:
              res.append(function(*args))
          else:
              return res
          idx = idx + 1
          print idx

def filter(function, collection):
    res = []
    if function is None:
       for elem in collection:
           if elem:
              res.append(elem)
    else:
       for elem in collection:
           if function(elem):
              res.append(elem)
    if type(collection) is tuple:
       return tuple(res)
    elif type(collection) is str:
       return "".join(res)
    else:
       return res

def zip(*collections):
    if len(collections) == 0:
       raise TypeError, "zip() requires at least one sequence"
    res = []
    while 1:
       try:
          elems = []
          for collection in collections:
             elems.append(collection.pop(0))
          res.append(tuple(elems))
       except IndexError:
          break
    return res


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
    if issubclass(klass_or_tuple.__class__, tuple):
       for klass in klass_or_tuple:
           if issubclass(objcls, klass):
              return 1
       return 0
    else:
       try:
          return issubclass(objcls, klass_or_tuple)
       except TypeError:
          raise TypeError, "isinstance() arg 2 must be a class or type"
 
def range(x, y=None, step=1):
    "docstring"

    if y is None:
        start = 0
        stop = x
    else:
        start = x
        stop = y

    arr = []
    i = start
    if step == 0:
        raise ValueError, 'range() arg 3 must not be zero'
    elif step > 0:
        while i < stop:
            arr.append(i)
            i += step
    else:
        while i > stop:
            arr.append(i)
            i += step

    return arr
