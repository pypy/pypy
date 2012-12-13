from pypy.annotation import model
from pypy.annotation.listdef import ListDef
from pypy.annotation.dictdef import DictDef


def none():
    return model.s_None


def float():
    return model.SomeFloat()

def singlefloat():
    return model.SomeSingleFloat()

def longfloat():
    return model.SomeLongFloat()


def int():
    return model.SomeInteger()


def basestring():
    return model.SomeStringOrUnicode()

def unicode():
    return model.SomeUnicodeString()

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

def dict(keytype, valuetype):
    dictdef = DictDef(None, keytype, valuetype)
    return model.SomeDict(dictdef)


def instance(class_):
    return lambda bookkeeper: model.SomeInstance(bookkeeper.getuniqueclassdef(class_))

class SelfTypeMarker(object):
    pass

def self():
    return SelfTypeMarker()
