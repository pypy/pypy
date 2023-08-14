def test_warn_globals_immutable(space):
    w_import = space.builtin.getdictvalue(space, '__import__')
    w_warnings = space.call_function(w_import, space.newtext("warnings"))
    # the test fails if the following line returns an ObjectMutableCell (which
    # has no .name)
    w_warn = w_warnings.w_dict.dstorage._x['warn']
    assert w_warn.name == 'warn'
    w_warn_explicit = w_warnings.w_dict.dstorage._x['warn_explicit']
    assert w_warn_explicit.name == 'warn_explicit'
