from pypy.objspace.std.stdtypedef import *


# ____________________________________________________________

basestring_typedef = StdTypeDef("basestring",
    __doc__ =  '''Type basestring cannot be instantiated; it is the base for str and unicode.'''                        
    )

