
def invoke(dyncode=False, assertion=False): 
    """ invoke magic, currently you can specify:

        dyncode    patches some syslibs and the compile builtins 
                   to support better traces for dynamically compiled
                   code. e.g. inspect.getsource(compile('...', ...))
                   should work. 

        assertion  patches the builtin AssertionError to try to give
                   more meaningful AssertionErrors, which by means
                   of deploying a mini-interpreter constructs
                   a useful error message. 
    """
    if dyncode:
        from py.__impl__.magic import dyncode 
        dyncode.invoke()
    if assertion: 
        from py.__impl__.magic import assertion 
        assertion.invoke()

def revoke(dyncode=False, assertion=False):
    """ revoke previously invoked magic (see invoke())."""
    if dyncode:
        from py.__impl__.magic import dyncode 
        dyncode.revoke()
    if assertion:
        from py.__impl__.magic import assertion 
        assertion.revoke()

