import autopath

def failing_app_test_import():
    import exceptions
    assert exceptions.SyntaxError is SyntaxError 
