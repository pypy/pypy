# replacement for decode_frame_arguments
#
# ===== ATTENTION =====
#
# This code is pretty fundamental to pypy and great care must be taken
# to avoid infinite recursion.  In particular:
#
# - All calls here must be "easy", i.e. not involve default or keyword
#   arguments.  For example, all range() calls need three arguments.
#
# - You cannot *catch* any exceptions (raising is fine).
#
# (I wonder if the pain of writing this at interpreter level might be
# worth it...)

def decode_code_arguments(args, kws, defs, closure, codeobject):
    """
    Assumptions:
    args = sequence of the normal actual parameters
    kws = dictionary of keyword actual parameters
    defs = sequence of defaults
    """
    CO_VARARGS = 0x4
    CO_VARKEYWORDS = 0x8
    varargs = (codeobject.co_flags & CO_VARARGS) and 1
    varkeywords = (codeobject.co_flags & CO_VARKEYWORDS) and 1
    varargs_tuple = ()
    
    argdict = {}
    parameter_names = codeobject.co_varnames[:codeobject.co_argcount]
    
    # Normal arguments
    for i in range(0, len(args), 1):    # see comment above for ", 1"
        if 0 <= i < len(parameter_names): # try
            argdict[parameter_names[i]] = args[i]
        else: # except IndexError:
            # If varargs, put in tuple, else throw error
            if varargs:
                varargs_tuple = args[i:]
            else:
                raise TypeError, 'Too many parameters to callable object'
            break

    # Put all suitable keywords into arglist
    if kws:
        if varkeywords:
            # Allow all keywords
            newkw = {}
            for key in kws.keys():
                for name in parameter_names:
                    if name == key:
                        if key in argdict:
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
                if name in kws:
                    count -= 1
                    if name in argdict:
                        raise TypeError, 'Setting parameter %s twice.' % name
                    else:
                        argdict[name] = kws[name]
            if count:
                # XXX This should be improved to show the parameters that
                #     shouldn't be here.
                raise TypeError, 'Setting keyword parameter that does not exist in formal parameter list.'
                
    # Fill in with defaults, starting at argcount - defcount
    if defs:
        argcount = codeobject.co_argcount
        defcount = len(defs)
        for i in range(argcount - defcount, argcount, 1): # ", 1" comment above
            if parameter_names[i] in argdict:
                continue
            argdict[parameter_names[i]] = defs[i - (argcount - defcount)]

    if len(argdict) < codeobject.co_argcount:
        raise TypeError, 'Too few parameters to callable object'

    namepos = codeobject.co_argcount
    if varargs:
        name = codeobject.co_varnames[namepos]
        argdict[name] = varargs_tuple
        namepos += 1
    if varkeywords:
        name = codeobject.co_varnames[namepos]
        argdict[name] = newkw

    return argdict
