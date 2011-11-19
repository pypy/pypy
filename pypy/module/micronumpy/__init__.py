from pypy.interpreter.mixedmodule import MixedModule


class Module(MixedModule):
    applevel_name = 'numpypy'

    interpleveldefs = {
        'array': 'interp_numarray.SingleDimArray',
        'dtype': 'interp_dtype.W_Dtype',
        'ufunc': 'interp_ufuncs.W_Ufunc',

        'zeros': 'interp_numarray.zeros',
        'empty': 'interp_numarray.zeros',
        'ones': 'interp_numarray.ones',
        'fromstring': 'interp_support.fromstring',

        'True_': 'types.Bool.True',
        'False_': 'types.Bool.False',

        'generic': 'interp_boxes.W_GenericBox',
        'number': 'interp_boxes.W_NumberBox',
        'integer': 'interp_boxes.W_IntegerBox',
        'signedinteger': 'interp_boxes.W_SignedIntegerBox',
        'bool_': 'interp_boxes.W_BoolBox',
        'int8': 'interp_boxes.W_Int8Box',
        'int_': 'interp_boxes.W_LongBox',
        'inexact': 'interp_boxes.W_InexactBox',
        'floating': 'interp_boxes.W_FloatingBox',
        'float64': 'interp_boxes.W_Float64Box',
    }

    # ufuncs
    for exposed, impl in [
        ("abs", "absolute"),
        ("absolute", "absolute"),
        ("add", "add"),
        ("arccos", "arccos"),
        ("arcsin", "arcsin"),
        ("arctan", "arctan"),
        ("arcsinh", "arcsinh"),
        ("arctanh", "arctanh"),
        ("copysign", "copysign"),
        ("cos", "cos"),
        ("divide", "divide"),
        ("equal", "equal"),
        ("exp", "exp"),
        ("fabs", "fabs"),
        ("floor", "floor"),
        ("greater", "greater"),
        ("greater_equal", "greater_equal"),
        ("less", "less"),
        ("less_equal", "less_equal"),
        ("maximum", "maximum"),
        ("minimum", "minimum"),
        ("multiply", "multiply"),
        ("negative", "negative"),
        ("not_equal", "not_equal"),
        ("reciprocal", "reciprocal"),
        ("sign", "sign"),
        ("sin", "sin"),
        ("subtract", "subtract"),
        ("tan", "tan"),
    ]:
        interpleveldefs[exposed] = "interp_ufuncs.get(space).%s" % impl

    appleveldefs = {
        'average': 'app_numpy.average',
        'mean': 'app_numpy.mean',
        'inf': 'app_numpy.inf',
        'e': 'app_numpy.e',
    }
