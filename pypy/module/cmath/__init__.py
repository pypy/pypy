
# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

names_and_docstrings = {
    'sqrt': "Return the square root of x.",
    'acos': "Return the arc cosine of x.",
    'acosh': "Return the hyperbolic arc cosine of x.",
    'asin': "Return the arc sine of x.",
    'asinh': "Return the hyperbolic arc sine of x.",
    }


class Module(MixedModule):
    appleveldefs = {
    }

    interpleveldefs = dict([(name, 'interp_cmath.wrapped_' + name)
                            for name in names_and_docstrings])
