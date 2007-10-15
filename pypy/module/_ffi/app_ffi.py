# NOT_RPYTHON

class Structure(object):
    def __init__(self, fields):
        self.fields = fields

    def __call__(self, **kwds):
        from _ffi import StructureInstance
        return StructureInstance(self.fields, kwds)

class StructureInstance(object):
    def __init__(self, shape, **kwds):
        self.shape = shape
        self.format = "".join([i[1] for i in shape])
        for kwd, value in kwds.items():
            setattr(self, kwd, value)

    def pack(self):
        args = [getattr(self, i[0], 0) for i in self.shape]
        return struct.pack(self.format, *args)

    def unpack(self, s):
        values = struct.unpack(self.format, s)
        for (name, _), value in zip(self.shape, values):
            setattr(self, name, value)
    
