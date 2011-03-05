from pypy.interpreter.mixedmodule import MixedModule
from pypy.module.array.interp_array import types, W_ArrayBase
from pypy.objspace.std.model import registerimplementation

for mytype in types.values():
    registerimplementation(mytype.w_class)


class Module(MixedModule):

    interpleveldefs = {
        'array': 'interp_array.W_ArrayBase',
        'ArrayType': 'interp_array.W_ArrayBase',
    }

    appleveldefs = {
    }
