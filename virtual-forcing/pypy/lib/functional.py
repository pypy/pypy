"""Higher order functions, and operations on callables.
   
    partial(fn,*args,**kw) - function resulting from partial application of a
        callable i.e. acts like that callable with some arguments already
        supplied.

    Examples:
        clamp = partial(max,0)                  # clamps negative values to zero
        whitecanv = partial(Canvas,bg='white')  # makes Canvases,white by default
        decapitate = partial(my_list.pop,0)     # pulls values of front of my list
        udp_sock = partial(socket,AF_INET,SOCK_DGRAM) # udp socket factory

    class Partial - an implementation of partial() as a class with callable
        instances. Attributes fn, args and kw can be modified.
        
   Peter Harris    April 2004

   function version of partial() using lambda suggested by David Abrams
"""

def partial(*args,**kw):
    """Return a version of a function with some arguments already supplied.
    """
    def merged(d1,d2):
        """Dictionary merge"""
        d = d1.copy()
        d.update(d2)
        return d
    fn = args[0]
    args = args[1:]
    return lambda *args2,**kw2: fn(*(args+args2),**merged(kw,kw2))

class Partial(object):
    """Callable with pre-supplied arguments"""
    def __init__(*args, **kw):
        self = args[0]
        self.fn, self.args, self.kw = (args[1], args[2:], kw)

    def __call__(self, *args, **kw):
        """Supply more positional arguments, override any keyword arguments
        already supplied"""
        if kw and self.kw:
            d = self.kw.copy()
            d.update(kw)
        else:
            d = kw or self.kw
        return self.fn(*(self.args + args), **d)
