
def signature(*paramtypes, **kwargs):
    """Decorate a function to specify its type signature.

    Usage:
      @signature(param1type, param2type, ..., returns=returntype)
      def foo(...)

    The arguments paramNtype and returntype should be instances
    of the classes in pypy.annotation.types.
    """
    returntype = kwargs.pop('returns', None)
    if returntype is None:
        raise TypeError, "signature: parameter 'returns' required"

    def decorator(f):
        f._signature_ = (paramtypes, returntype)
        return f
    return decorator
