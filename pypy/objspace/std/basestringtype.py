from pypy.interpreter.typedef import TypeDef


basestring_typedef = TypeDef("basestring",
    __doc__ =  ("basestring cannot be instantiated; "
                "it is the base for str and unicode.")
    )
