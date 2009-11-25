from pypy.rpython.ootypesystem.ootype import ROOT, Instance, \
     addMethods, meth, Meth, Void
from pypy.translator.backendopt.checkvirtual import check_virtual_methods

def test_nonvirtual():
    A = Instance("A", ROOT)
    addMethods(A, {"foo": meth(Meth([], Void))})

    check_virtual_methods()
    assert A._methods["foo"]._virtual == False

def test_checkvirtual_simple():
    A = Instance("A", ROOT)
    B = Instance("B", A)

    addMethods(A, {"foo": meth(Meth([], Void)),
                   "bar": meth(Meth([], Void))})
    
    addMethods(B, {"foo": meth(Meth([], Void))})

    check_virtual_methods()
    assert A._methods["foo"]._virtual == True
    assert A._methods["bar"]._virtual == False
    assert B._methods["foo"]._virtual == False

def test_checkvirtual_deep():
    A = Instance("A", ROOT)
    B = Instance("B", A)
    C = Instance("C", B)

    addMethods(A, {"foo": meth(Meth([], Void)),
                   "bar": meth(Meth([], Void))})
    
    addMethods(C, {"foo": meth(Meth([], Void))})

    check_virtual_methods()
    assert A._methods["foo"]._virtual == True
    assert A._methods["bar"]._virtual == False
    assert "foo" not in B._methods
    assert C._methods["foo"]._virtual == False

def test_checkvirtual_brother():
    A = Instance("A", ROOT)
    B1 = Instance("B1", A)
    B2 = Instance("B2", A)

    addMethods(A, {"foo": meth(Meth([], Void)),
                   "bar": meth(Meth([], Void))})
    
    addMethods(B1, {"foo": meth(Meth([], Void))})

    check_virtual_methods()
    assert A._methods["foo"]._virtual == True
    assert A._methods["bar"]._virtual == False
    assert B1._methods["foo"]._virtual == False
    assert "foo" not in B2._methods

