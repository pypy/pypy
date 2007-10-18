# NOT_RPYTHON

class Structure(object):
    def check_fields(self, fields):
        import _ffi
        for name, letter in fields:
            _ffi._get_type(letter)
    
    def __init__(self, fields):
        self.check_fields(fields)
        self.fields = fields

    def __call__(self, *args, **kwds):
        from _ffi import StructureInstance
        if args:
            if len(args) > 1:
                raise TypeError("Can give at most one non-keyword argument")
            if kwds:
                raise TypeError("Keyword arguments not allowed when passing address argument")
            return StructureInstance(self, args[0], None)
        return StructureInstance(self, None, kwds)

class Array(object):
    def __init__(self, of):
        import _ffi
        self.of = of
        _ffi._get_type(of)

    def __call__(self, size):
        from _ffi import ArrayInstance
        return ArrayInstance(self.of, size)
