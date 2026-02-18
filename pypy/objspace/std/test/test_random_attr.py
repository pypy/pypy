from rpython.rlib import objectmodel
from pypy.objspace.std.mapdict import (
        _make_storage_mixin_size_n,
       BaseUserClassMapdict, MapdictDictSupport, MapdictStorageMixin)
from pypy.objspace.std.test.test_mapdict import Class
from pypy.objspace.std.objectobject import W_ObjectObject
from pypy.objspace.std.test.test_dictmultiobject import FakeSpace

import pytest
import sys
try:
    from hypothesis import given, strategies, settings, example
except ImportError:
    pytest.skip("requires hypothesis")

base_initargs = strategies.sampled_from([
    ("object", (), False),
    ("type(sys)", ("fake", ), True),
    ("NewBase", (), True),
    ("OldBase", (), False),
    ("object, OldBase", (), False),
    ("type(sys), OldBase", ("fake", ), True),
    ])

attrnames = strategies.sampled_from(["a", "b", "c"] + ["attr%s" % i for i in range(10)])

def make_value_attr(val):
    return val, str(val)

def make_method(val):
    return (lambda self, val=val: val,
            "lambda self: %d" % val)

def make_property(val):
    return (
        property(lambda self: val, lambda self, val: None, lambda self: None),
        "property(lambda self: %d, lambda self, val: None, lambda self: None)" % val)

value_attrs = strategies.builds(make_value_attr, strategies.integers())
methods = strategies.builds(make_method, strategies.integers())
properties = strategies.builds(make_property, strategies.integers())
class_attrs = strategies.one_of(value_attrs, methods, properties)


@strategies.composite
def make_code(draw):
    baseclass, initargs, hasdict = draw(base_initargs)

    code = ["import sys", "class OldBase:pass", "class NewBase(object):pass", "class A(%s):" % baseclass]
    dct = {}
    if draw(strategies.booleans()):
        slots = draw(strategies.lists(attrnames))
        if not hasdict and draw(strategies.booleans()):
            slots.append("__dict__")
        dct["__slots__"] = slots
        code.append("    __slots__ = %s" % (slots, ))
    for name in ["a", "b", "c"]:
        if not draw(strategies.booleans()):
            continue
        dct[name], codeval = draw(class_attrs)
        code.append("    %s = %s" % (name, codeval))
    class OldBase: pass
    class NewBase(object): pass
    evaldct = {'OldBase': OldBase, 'NewBase': NewBase}
    if baseclass == 'OldBase':
        metaclass = type(OldBase)
    else:
        metaclass = type
    cls = metaclass("A", eval(baseclass+',', globals(), evaldct), dct)
    inst = cls(*initargs)
    code.append("    pass")
    code.append("a = A(*%s)" % (initargs, ))
    for attr in draw(strategies.lists(attrnames, min_size=10)):
        op = draw(strategies.sampled_from(["read", "read", "read",
                      "write", "write", "write", "del", "del", "writemeth",
                      "writeclass", "writebase", "delclass"]))
        if op == "read":
            try:
                res = getattr(inst, attr)
            except AttributeError:
                code.append("raises(AttributeError, 'a.%s')" % (attr, ))
            else:
                if callable(res):
                    code.append("assert a.%s() == %s" % (attr, res()))
                else:
                    code.append("assert a.%s == %s" % (attr, res))
        elif op == "write":
            val = draw(strategies.integers())
            try:
                setattr(inst, attr, val)
            except AttributeError:
                code.append("raises(AttributeError, 'a.%s=%s')" % (attr, val))
            else:
                code.append("a.%s = %s" % (attr, val))
        elif op == "writemeth":
            val = draw(strategies.integers())
            try:
                setattr(inst, attr, lambda val=val: val)
            except AttributeError:
                code.append("raises(AttributeError, 'a.%s=0')" % (attr, ))
            else:
                code.append("a.%s = lambda : %s" % (attr, val))
        elif op == "writeclass":
            val, codeval = draw(class_attrs)
            setattr(cls, attr, val)
            code.append("A.%s = %s" % (attr, codeval))
        elif op == "writebase":
            val, codeval = draw(class_attrs)
            setattr(OldBase, attr, val)
            setattr(NewBase, attr, val)
            code.append("OldBase.%s = NewBase.%s = %s" % (attr, attr , codeval))
        elif op == "del":
            try:
                delattr(inst, attr)
            except AttributeError:
                code.append("raises(AttributeError, 'del a.%s')" % (attr, ))
            else:
                code.append("del a.%s" % (attr, ))
        elif op == "delclass":
            try:
                delattr(cls, attr)
            except AttributeError:
                code.append("raises(AttributeError, 'del A.%s')" % (attr, ))
            else:
                code.append("del A.%s" % (attr, ))
    return "\n    ".join(code)


@given(code=make_code())
#@settings(max_examples=5000)
def test_random_attrs(code, space):
    print code
    exec "if 1:\n    " + code
    space.appexec([], "():\n    " + code)



@strategies.composite
def make_sequence(draw):
    n_attributes = draw(strategies.integers(min_value=1, max_value=100))
    attributes = ["s%s" % i for i in range(n_attributes)]
    model = {}
    steps = []
    for i in range(draw(strategies.integers(min_value=2, max_value=1000))):
        if not model:
            op = "set"
        else:
            op = draw(strategies.sampled_from(["set", "del"]))
        if op == "set":
            attr = draw(strategies.sampled_from(attributes))
            valuekind = draw(strategies.sampled_from(["obj", "int", "float"]))
            if valuekind == "obj":
                value = draw(strategies.sampled_from(["a", "b", "c", "d"]))
            elif valuekind == "int":
                value = draw(strategies.integers())
            elif valuekind == "float":
                value = draw(strategies.floats())
            model[attr] = value
            steps.append((op, attr, value))
        elif op == "del":
            attr = draw(strategies.sampled_from(sorted(model)))
            del model[attr]
            steps.append((op, attr, None))
    return steps

class objectcls(W_ObjectObject):
    objectmodel.import_from_mixin(BaseUserClassMapdict)
    objectmodel.import_from_mixin(MapdictDictSupport)
    objectmodel.import_from_mixin(_make_storage_mixin_size_n(5))

class genericstoragecls(W_ObjectObject):
    objectmodel.import_from_mixin(BaseUserClassMapdict)
    objectmodel.import_from_mixin(MapdictDictSupport)
    objectmodel.import_from_mixin(MapdictStorageMixin)

space = FakeSpace()

@given(make_sequence())
def test_random_attrs_lowlevel_objclass(sequence):
    try:
        run_test(objectcls, sequence)
    except Exception:
        raise

@given(make_sequence())
def test_random_attrs_lowlevel_generic(sequence):
    try:
        run_test(genericstoragecls, sequence)
    except Exception:
        raise

def run_test(objcls, sequence):
    cls = Class(allow_unboxing=True)
    obj = objcls()
    obj.user_setup(space, cls)
    print sequence
    model = {}
    for i, (what, attr, value) in enumerate(sequence):
        if i == 52:
            import pdb;pdb.set_trace()
        if what == "set":
            obj.setdictvalue(space, attr, value)
            model[attr] = value
        elif what == "del":
            obj.deldictvalue(space, attr)
            del model[attr]

        for name, value in model.iteritems():
            assert repr(obj.getdictvalue(space, name)) == repr(value)
        if hasattr(obj, 'storage'):
            if obj.map.storage_needed():
                assert obj.map.storage_needed() == len(obj.storage)

