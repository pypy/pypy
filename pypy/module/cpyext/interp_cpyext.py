from .methodobject import W_PyCFunctionObject, W_PyCMethodObject

def is_cpyext_builtin_function(space, w_arg):
    return space.newbool(
        isinstance(w_arg, W_PyCFunctionObject) and
        not isinstance(w_arg, W_PyCMethodObject)
    )
