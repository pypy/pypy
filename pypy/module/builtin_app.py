def apply(function, args, kwds={}):
    """call a function (or other callable object) and return its result"""
    return function(*args, **kwds)

def map(function, *collections):
    """does 3 separate things, hence this enormous docstring.
       1.  if function is None, return a list of tuples, each with one
           item from each collection.  If the collections have different
           lengths,  shorter ones are padded with None.

       2.  if function is not None, and there is only one collection,
           apply function to every item in the collection and return a
           list of the results.

       3.  if function is not None, and there are several collections,
           repeatedly call the function with one argument from each
           collection.  If the collections have different lengths,
           shorter ones are padded with None"""

    if len(collections) == 0:
        raise TypeError, "map() requires at least one sequence"
    
    elif len(collections) == 1:
       #it's the most common case, so make it faster
       if function is None:
          return collections[0]
       else:
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
              if function is None:
                 res.append(tuple(args))
              else:
                 res.append(function(*args))
          else:
              return res
          idx = idx + 1

def filter(function, collection):
    """construct a list of those elements of collection for which function
       is True.  If function is None, then return the items in the sequence
       which are True."""
     
    if function is None:
        res = [item for item in collection if item]
    else:
        res = [item for item in collection if function(item)]
              
    if type(collection) is tuple:
       return tuple(res)
    elif type(collection) is str:
       return "".join(res)
    else:
       return res

def zip(*collections):
    """return a list of tuples, where the nth tuple contains every
       nth item of each collection.  If the collections have different
       lengths, zip returns a list as long as the shortest collection,
       ignoring the trailing items in the other collections."""
    
    if len(collections) == 0:
       raise TypeError, "zip() requires at least one sequence"
    res = []
    idx = 0
    while 1:
       try:
          elems = []
          for collection in collections:
             elems.append(collection[idx])
          res.append(tuple(elems))
       except IndexError:
          break
       idx = idx + 1
    return res

def reduce(function, l, *initialt):
    """ Apply function of two arguments cumulatively to the items of
        sequence, from left to right, so as to reduce the sequence to a
        single value.  Optionally begin with an initial value."""
    
    if initialt:
       initial, = initialt
       idx = 0
    else:
       try:
          initial = l[0]
       except IndexError:
          raise TypeError, "reduce() of empty sequence with no initial value"
       idx = 1
    while 1:
       try:
         initial = function(initial, l[idx])
         idx = idx + 1
       except IndexError:
         break
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
    """ returns a list of integers in arithmetic position from start (defaults
        to zero) to stop - 1 by step (defaults to 1).  Use a negative step to
        get a list in decending order."""

    if y is None: 
            start = 0
            stop = x
    else:
            start = x
            stop = y

    if step == 0:
        raise ValueError, 'range() arg 3 must not be zero'

    elif step > 0:
        if stop <= start: # no work for us
            return []
        howmany = (stop - start + step - 1)/step

    else:  # step must be < 0, or we would have raised ValueError
        if stop >= start: # no work for us
            return []
        howmany = (start - stop - step  - 1)/-step
       
    arr = [None] * howmany  # this is to avoid using append.

    i = start
    n = 0
    while n < howmany:
        arr[n] = i
        i += step
        n += 1

    return arr

# min and max could be one function if we had operator.__gt__ and
# operator.__lt__  Perhaps later when we have operator.

def min(*arr):
    """return the smallest number in a list"""

    if not arr:
        raise TypeError, 'min() takes at least one argument'

    if len(arr) == 1:
        arr = arr[0]
     
    iterator = iter(arr)
    try:
        min = iterator.next()
    except StopIteration:
        raise ValueError, 'min() arg is an empty sequence'
    
    for i in iterator:
        if min > i:
            min = i
    return min

def max(*arr):
    """return the largest number in a list"""

    if not arr:
        raise TypeError, 'max() takes at least one argument'

    if len(arr) == 1:
        arr = arr[0]

    iterator = iter(arr)
    try:
        max = iterator.next()
    except StopIteration:
        raise ValueError, 'max() arg is an empty sequence'

    for i in iterator:
        if max < i:
            max = i
    return max


def cmp(x, y):
    """return 0 when x == y, -1 when x < y and 1 when x > y """
    if x < y:
        return -1
    elif x == y:
        return 0
    else:
        return 1

def vars(*obj):
    """return a dictionary of all the attributes currently bound in obj.  If
    called with no argument, return the variables bound in local scope."""

    if len(obj) == 0:
        return locals()
    elif len(obj) != 1:
        raise TypeError, "vars() takes at most 1 argument."
    else:
        try:
            return obj[0].__dict__
        except AttributeError:
            raise TypeError, "vars() argument must have __dict__ attribute"
