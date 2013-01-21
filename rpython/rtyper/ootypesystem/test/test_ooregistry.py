from rpython.annotator.annrpython import RPythonAnnotator
from rpython.annotator import model as annmodel
from rpython.rtyper.ootypesystem import ooregistry # side effects
from rpython.rtyper.ootypesystem import ootype
from rpython.rtyper.test.test_llinterp import interpret

def test_oostring_annotation():
    def oof():
        return ootype.oostring

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    assert isinstance(s, annmodel.SomeBuiltin)

def test_oostring_result_annotation():
    def oof():
        return ootype.oostring(42, -1)

    a = RPythonAnnotator()
    s = a.build_types(oof, [])
    assert isinstance(s, annmodel.SomeOOInstance) and s.ootype is ootype.String

def test_oostring_call():
    def oof(ch):
        return ootype.oostring(ch, -1)

    ch = 'a'
    res = interpret(oof, [ch], type_system='ootype')
    assert res._str == 'a'
