import autopath

def app_test_import():
    import exceptions
    assert exceptions.SyntaxError is SyntaxError 
