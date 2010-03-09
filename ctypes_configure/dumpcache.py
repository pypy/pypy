import os
import ctypes


def dumpcache(referencefilename, filename, config):
    dirname = os.path.dirname(referencefilename)
    filename = os.path.join(dirname, filename)
    f = open(filename, 'w')
    print >> f, 'import ctypes'
    print >> f
    names = config.keys()
    names.sort()
    print >> f, '__all__ = %r' % (tuple(names),)
    print >> f
    for key in names:
        val = config[key]
        if isinstance(val, (int, long)):
            f.write("%s = %d\n" % (key, val))
        elif val is None:
            f.write("%s = None\n" % key)
        elif isinstance(val, ctypes.Structure.__class__):
            f.write("class %s(ctypes.Structure):\n" % key)
            f.write("    _fields_ = [\n")
            for k, v in val._fields_:
                f.write("        ('%s', %s),\n" % (k, ctypes_repr(v)))
            f.write("    ]\n")
        elif isinstance(val, (tuple, list)):
            for x in val:
                assert isinstance(x, (int, long, str)), \
                       "lists of integers or strings only"
            f.write("%s = %r\n" % (key, val))
        else:
            # a simple type, hopefully
            f.write("%s = %s\n" % (key, ctypes_repr(val)))
    f.close()
    print 'Wrote %s.' % (filename,)

def ctypes_repr(cls):
    # ctypes_configure does not support nested structs so far
    # so let's ignore it
    if isinstance(cls, ctypes._SimpleCData.__class__):
        return "ctypes." + cls.__name__
    if hasattr(cls, '_length_') and hasattr(cls, '_type_'):  # assume an array
        return '%s*%d' % (ctypes_repr(cls._type_), cls._length_)
    raise NotImplementedError("saving of object with type %r" % type(cls))
