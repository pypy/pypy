import pytest
import sys
from pypy.tool.pytest.objspace import gettestobjspace
try:
    from hypothesis import given, strategies, settings
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

attrnames = strategies.sampled_from(["a", "b", "c"])

@strategies.composite
def make_code(draw):
    # now here we can do this kind of thing:
    baseclass, initargs, hasdict = draw(base_initargs)
    # and with arbitrary strategies

    def class_attr():
        what = draw(strategies.sampled_from(["value", "method", "property"]))
        if what == "value":
            val = draw(strategies.integers())
            return val, str(val)
        if what == "method":
            val = draw(strategies.integers())
            return (lambda self, val=val: val,
                    "lambda self: %d" % val)
        if what == "property":
            val = draw(strategies.integers())
            return (property(lambda self, val=val: val,
                             lambda self, val: None,
                             lambda self: None),
                    "property(lambda self: %d, lambda self, val: None, lambda self: None)" % val)

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
        dct[name], codeval = class_attr()
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
    for attr in draw(strategies.lists(attrnames, min_size=1)):
        op = draw(strategies.sampled_from(["read", "read", "read",
                      "write", "writemeth", "writeclass", "writebase",
                      "del", "delclass"]))
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
            val, codeval = class_attr()
            setattr(cls, attr, val)
            code.append("A.%s = %s" % (attr, codeval))
        elif op == "writebase":
            val, codeval = class_attr()
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


@given(make_code())
#@settings(max_examples=5000)
def test_random_attrs(code):
    try:
        import __pypy__
    except ImportError:
        pass
    else:
        pytest.skip("makes no sense under pypy!")
    space = gettestobjspace()
    print code
    exec "if 1:\n    " + code
    space.appexec([], "():\n    " + code)
