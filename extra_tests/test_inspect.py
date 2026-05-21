import inspect, types

def test_object_init_signature():
    sig = inspect.signature(object.__init__)
    params = list(sig.parameters.values())
    first = params[0]
    assert first.name == 'self'
    assert first.kind == inspect.Parameter.POSITIONAL_ONLY

def test_object_new_signature():
    sig = inspect.signature(object.__new__)
    params = list(sig.parameters.values())
    first = params[0]
    assert first.name == 'args'
    assert first.kind == inspect.Parameter.VAR_POSITIONAL

def test_signature_builtin_types():
    assert str(inspect.signature(complex)).startswith('(real')
    assert str(inspect.signature(types.CodeType)).startswith('(argcount, posonlyargcount, kwonlyargcount, nlocals, stacksize, flags,')
    assert inspect.signature(types.CodeType) == inspect.signature(types.CodeType.__new__)

def test_cpyext_fails():
    # issue gh-5227
    import _testcapi
    assert inspect.isbuiltin(_testcapi.set_errno)
    
