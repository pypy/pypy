from _numpypy.multiarray import *
from _numpypy.umath import *

newaxis = None
ufunc = type(sin)

types = ['bool8', 'byte', 'ubyte', 'short', 'ushort', 'longlong', 'ulonglong',
         'single', 'double', 'longfloat', 'longdouble',
         'csingle', 'cdouble', 'cfloat', 'clongdouble',
         'void']
for t in ('int', 'uint'):
    for s in (8, 16, 32, 64, 'p'):
        types.append(t + str(s))
for s in (16, 32, 64):
    types.append('float' + str(s))
for s in (64, 128):
    types.append('complex' + str(s))
for t in types:
    globals()[t] = dtype(t).type

types = ['bool', 'int', 'float', 'complex', 'str', 'unicode']
for t in types:
    globals()[t + '_'] = dtype(t).type
del types

types = ['Generic', 'Number', 'Integer', 'SignedInteger', 'UnsignedInteger',
         'Inexact', 'Floating', 'ComplexFloating', 'Character']
for t in types:
    globals()[t.lower()] = typeinfo[t]

True_ = bool_(True)
False_ = bool_(False)
