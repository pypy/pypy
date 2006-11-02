
""" example of (very simple) serialiser
"""

def serialise(obj):
    if isinstance(obj, str):
        return "S" + obj
    elif isinstance(obj, int):
        return "I" + str(obj)
    return "?"

serialise._annspecialcase_ = "specialize:argtype(0)"

def serialisetest():
    return serialise("aaa") + serialise(3) + serialise(None)
