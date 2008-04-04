from pypy.translator.translator import graphof

# ___________________________________________________________________________

HELPERS = {}
def with_types(type_list):
    def decorator(func):
        HELPERS[func] = type_list
        return func
    return decorator

@with_types([])
def throwZeroDivisionError():
    raise ZeroDivisionError

@with_types([])
def throwIndexError():
    raise IndexError

@with_types([])
def throwOverflowError():
    raise OverflowError

@with_types([])
def throwRuntimeError():
    raise RuntimeError

@with_types([])
def throwMemoryError():
    raise MemoryError

@with_types([])
def throwValueError():
    raise ValueError

@with_types([])
def throwUnicodeDecodeError():
    raise UnicodeDecodeError

@with_types([str, str])
def recordStringString(a, b):
    return (a, b)

@with_types([float, float])
def recordFloatFloat(a, b):
    return (a, b)

@with_types([float, int])
def recordFloatSigned(a, b):
    return (a, b)

@with_types([int, int])
def recordSignedSigned(a, b):
    return (a, b)

# ___________________________________________________________________________

def create_interlink_node(db):
    """ Translates the create_interlink_impl() function and returns
    a jvm.Method object that allows it to be called. """
    translator = db.genoo.translator

    for func, type_list in HELPERS.items():
        translator.annotator.build_types(func, type_list) 
    translator.rtyper.specialize_more_blocks()

    helpers = {}
    for func in HELPERS.keys():
        graph = graphof(translator, func)
        helpers[func.func_name] = db.pending_function(graph)

    raise_OSError_graph = translator.rtyper.exceptiondata.fn_raise_OSError.graph
    helpers["throwOSError"] = db.pending_function(raise_OSError_graph)

    db.create_interlink_node(helpers)

