
""" extdesc - some descriptions for external entries
"""

from pypy.annotation.signature import annotation

class ArgDesc(object):
    """ Description of argument, given as name + example value
    (used to deduce type)
    """
    def __init__(self, name, _type):
        self.name = name
        self._type = _type
    
    def __repr__(self):
        return "<ArgDesc %s: %s>" % (self.name, self._type)

class MethodDesc(object):
    """ Description of method to be external,
    args are taken from examples given as keyword arguments or as args,
    return value must be specified, because this will not be flown
    """
    def __init__(self, args, retval = None):
        self.num = 0
        self.args = [self.convert_val(arg) for arg in args]
        self.retval = self.convert_val(retval)
        self.example = self
    
    def convert_val(self, val):
        if isinstance(val, ArgDesc) or isinstance(val, MethodDesc):
            return val
        elif isinstance(val, tuple):
            return ArgDesc(*val)
        else:
            self.num += 1
            return ArgDesc('v%d' % (self.num-1), val)

    def __repr__(self):
        return "<MethodDesc (%r)>" % (self.args,)
