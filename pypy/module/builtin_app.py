
# XXX kwds yet to come

# Problem: need to decide how to implement iterators,
# which are needed for star args.

def apply(function, args):#, kwds):
    return function(*args)#, **kwds)

def map(function, list):
    "docstring"
    return [function(x) for x in list]
