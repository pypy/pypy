from exceptions import TypeError

"""
Assumptions:
args = sequence of the normal actual parameters
kws = dictionary of keyword actual parameters
defs = sequence of defaults
"""
def decode_frame_arguments(args, kws, defs, closure, codeobject):
    CO_VARARGS = 0x4
    CO_VARKEYWORDS = 0x8
    varargs = (codeobject.co_flags & CO_VARARGS) and 1
    varkeywords = (codeobject.co_flags & CO_VARKEYWORDS) and 1
    varargs_tuple = ()
    
    argdict = {}
    parameter_names = codeobject.co_varnames[:codeobject.co_argcount]
    
    # Normal arguments
    for i in range(len(args)):
        try:
            argdict[parameter_names[i]] = args[i]
        except IndexError:
            # If varargs, put in tuple, else throw error
            if varargs:
                varargs_tuple = args[i:]
            else:
                raise TypeError, 'Too many parameters to callable object'

    # Put all suitable keywords into arglist
    if kws:
        if varkeywords:
            # Allow all keywords
            newkw = {}
            for key in kws.keys():
                for name in parameter_names:
                    if name == key:
                        if argdict.has_key(key):
                            raise TypeError, 'Setting parameter %s twice.' % name
                        else:
                            argdict[key] = kws[key]
                        break # name found in parameter names
                else:
                    newkw[key] = kws[key]
                    
        else:
            # Only allow formal parameter keywords
            count = len(kws)
            for name in parameter_names:
                if kws.has_key(name):
                    count -= 1
                    if argdict.has_key(name):
                        raise TypeError, 'Setting parameter %s twice.' % name
                    else:
                        argdict[name] = kws[name]
            if count:
                # XXX This should be improved to show the parameters that
                #     shouldn't be here.
                raise TypeError, 'Setting keyword parameter that does not exist in formal parameter list.'
                
    # Fill in with defaults, starting at argcount - defcount
    if defs:
        argcount = len(codeobject.co_varnames)
        defcount = len(defs)
        for i in range(argcount - defcount, argcount):
            if argdict.has_key(parameter_names[i]):
                continue
            argdict[parameter_names[i]] = defs[i - (argcount - defcount)]

    if len(argdict) < codeobject.co_argcount:
        raise TypeError, 'Too few paramteres to callable object'

    a = [argdict[name] for name in parameter_names]
    if varargs:
        a.append(varargs_tuple)
    if varkeywords:
        a.append(newkw)
    return tuple(a)
