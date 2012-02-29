import operator

def bin(x):
    x = operator.index(x)
    return x.__format__("#b")
