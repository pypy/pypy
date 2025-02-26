import inspect, types

def test_signature_builtin_types():
    assert str(inspect.signature(complex)).startswith('(real')
    assert str(inspect.signature(types.CodeType)).startswith('(argcount, posonlyargcount, kwonlyargcount, nlocals, stacksize, flags,')
    assert inspect.signature(types.CodeType) == inspect._signature_bound_method(inspect.signature(types.CodeType.__new__))

def test_cpyext_fails():
    # issue gh-5227
    import _testcapi
    assert inspect.isbuiltin(_testcapi.set_errno)
    
