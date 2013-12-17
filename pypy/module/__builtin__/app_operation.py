import operator

def bin(x):
    value = operator.index(x)
    return value.__format__("#b")
