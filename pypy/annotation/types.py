from pypy.annotation import model
from pypy.annotation.listdef import ListDef


def float():
    return model.SomeFloat()

def singlefloat():
    return model.SomeSingleFloat()

def longfloat():
    return model.SomeLongFloat()


def int():
    return model.SomeInteger()


def str():
    return model.SomeString()

def char():
    return model.SomeChar()


def list(element):
    listdef = ListDef(None, element, mutated=True, resized=True)
    return model.SomeList(listdef)

def array(element):
    listdef = ListDef(None, element, mutated=True, resized=False)
    return model.SomeList(listdef)


def instance(class_):
    return lambda bookkeeper: model.SomeInstance(bookkeeper.getuniqueclassdef(class_))
