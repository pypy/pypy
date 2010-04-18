from pypy.objspace.std.stdtypedef import StdTypeDef


basestring_typedef = StdTypeDef("basestring",
    __doc__ =  ("basestring cannot be instantiated; "
                "it is the base for str and unicode.")
    )
