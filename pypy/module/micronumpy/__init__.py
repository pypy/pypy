from pypy.interpreter.mixedmodule import MixedModule


class MultiArrayModule(MixedModule):
    appleveldefs = {'arange': 'app_numpy.arange'}
    interpleveldefs = {
        'ndarray': 'interp_numarray.W_NDimArray',
        'dtype': 'interp_dtype.W_Dtype',

        'array': 'interp_numarray.array',
        'zeros': 'interp_numarray.zeros',
        'empty': 'interp_numarray.zeros',
        'empty_like': 'interp_numarray.empty_like',
        '_reconstruct' : 'interp_numarray._reconstruct',
        'scalar' : 'interp_numarray.build_scalar',
        'dot': 'interp_arrayops.dot',
        'fromstring': 'interp_support.fromstring',
        'flatiter': 'interp_flatiter.W_FlatIterator',
        'concatenate': 'interp_arrayops.concatenate',
        'where': 'interp_arrayops.where',
        'count_nonzero': 'interp_arrayops.count_nonzero',

        'set_string_function': 'appbridge.set_string_function',
        'typeinfo': 'interp_dtype.get_dtype_cache(space).w_typeinfo',
    }


class UMathModule(MixedModule):
    appleveldefs = {}
    interpleveldefs = {'FLOATING_POINT_SUPPORT': 'space.wrap(1)'}
    # ufuncs
    for exposed, impl in [
        ("absolute", "absolute"),
        ("add", "add"),
        ("arccos", "arccos"),
        ("arcsin", "arcsin"),
        ("arctan", "arctan"),
        ("arctan2", "arctan2"),
        ("arccosh", "arccosh"),
        ("arcsinh", "arcsinh"),
        ("arctanh", "arctanh"),
        ("conj", "conjugate"),
        ("conjugate", "conjugate"),
        ("copysign", "copysign"),
        ("cos", "cos"),
        ("cosh", "cosh"),
        ("divide", "divide"),
        ("true_divide", "true_divide"),
        ("equal", "equal"),
        ("exp", "exp"),
        ("exp2", "exp2"),
        ("expm1", "expm1"),
        ("fabs", "fabs"),
        ("fmax", "fmax"),
        ("fmin", "fmin"),
        ("fmod", "fmod"),
        ("floor", "floor"),
        ("ceil", "ceil"),
        ("trunc", "trunc"),
        ("greater", "greater"),
        ("greater_equal", "greater_equal"),
        ("less", "less"),
        ("less_equal", "less_equal"),
        ("maximum", "maximum"),
        ("minimum", "minimum"),
        ("mod", "mod"),
        ("multiply", "multiply"),
        ("negative", "negative"),
        ("not_equal", "not_equal"),
        ("radians", "radians"),
        ("degrees", "degrees"),
        ("deg2rad", "radians"),
        ("rad2deg", "degrees"),
        ("reciprocal", "reciprocal"),
        ("rint", "rint"),
        ("sign", "sign"),
        ("signbit", "signbit"),
        ("sin", "sin"),
        ("sinh", "sinh"),
        ("subtract", "subtract"),
        ('sqrt', 'sqrt'),
        ('square', 'square'),
        ("tan", "tan"),
        ("tanh", "tanh"),
        ('bitwise_and', 'bitwise_and'),
        ('bitwise_or', 'bitwise_or'),
        ('bitwise_xor', 'bitwise_xor'),
        ('bitwise_not', 'invert'),
        ('left_shift', 'left_shift'),
        ('right_shift', 'right_shift'),
        ('invert', 'invert'),
        ('isnan', 'isnan'),
        ('isinf', 'isinf'),
        ('isfinite', 'isfinite'),
        ('logical_and', 'logical_and'),
        ('logical_xor', 'logical_xor'),
        ('logical_not', 'logical_not'),
        ('logical_or', 'logical_or'),
        ('log', 'log'),
        ('log2', 'log2'),
        ('log10', 'log10'),
        ('log1p', 'log1p'),
        ('power', 'power'),
        ('floor_divide', 'floor_divide'),
        ('logaddexp', 'logaddexp'),
        ('logaddexp2', 'logaddexp2'),
        ('real', 'real'),
        ('imag', 'imag'),
    ]:
        interpleveldefs[exposed] = "interp_ufuncs.get(space).%s" % impl


class Module(MixedModule):
    applevel_name = '_numpypy'
    appleveldefs = {}
    interpleveldefs = {}
    submodules = {
        'multiarray': MultiArrayModule,
        'umath': UMathModule,
    }
