# NOT_RPYTHON

class Structure(object):
    def __init__(self, fields):
        self.fields = fields

    def __call__(self, **kwds):
        from _ffi import StructureInstance
        return StructureInstance(self, kwds)
