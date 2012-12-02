from pypy.annotation import model


def int():
    return model.SomeInteger()

def str():
    return model.SomeString()
