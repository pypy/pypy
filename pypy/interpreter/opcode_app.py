def prepare_raise0():
    import sys
    return sys.exc_info()
    
def prepare_raise(etype, value, traceback):
    import types
    # XXX we get an infinite loop if this import fails:
    #    import types -> IMPORT_NAME -> import_name -> raise ImportError
    #    -> RAISE_VARARGS -> prepare_raise -> import types ...
    if  not isinstance(traceback, (types.NoneType, types.TracebackType)):
            raise TypeError, "raise: arg 3 must be traceback or None"
    while isinstance(etype, tuple):
        etype = etype[0]
    if type(etype) is str:
        # warn
        pass
    elif isinstance(etype, types.ClassType):
        if value is None:
            value = ()
        elif not isinstance(value, tuple):
            value = (value,)
        value = etype(*value)
    elif isinstance(etype, types.InstanceType):
        if value is not None:
            raise TypeError, "instance exception may not have a separate value"
        value = etype
        etype = value.__class__
    else:
        raise TypeError, "exceptions must be classes, instances, or " \
              "strings (deprecated), not %s"%(type(etype).__name__,)
    return etype, value, traceback

def build_class(methods, bases, name):
    import new
    return new.classobj(name, bases, methods)

def print_expr(x):
    import sys
    try:
        displayhook = sys.displayhook
    except AttributeError:
        raise RuntimeError, "lost sys.displayhook"
    displayhook(x)


def file_softspace(file, newflag):
    softspace = getattr(file, "softspace", False)
    try:
        file.softspace = newflag
    except AttributeError:
        pass
    return softspace

def print_item_to(x, stream):
    if file_softspace(stream, False):
        stream.write(" ")
    stream.write(str(x))
    # add a softspace unless we just printed a string which ends in a '\t'
    # or '\n' -- or more generally any whitespace character but ' '
    if isinstance(x, str) and x[-1].isspace() and x[-1]!=' ':
        return
    # XXX add unicode handling
    file_softspace(stream, True)

def print_item(x):
    import sys
    try:
        stream = sys.stdout
    except AttributeError:
        raise RuntimeError, "lost sys.stdout"
    print_item_to(x, stream)

def print_newline_to(stream):
    stream.write("\n")
    file_softspace(stream, False)

def print_newline():
    import sys
    try:
        stream = sys.stdout
    except AttributeError:
        raise RuntimeError, "lost sys.stdout"
    print_newline_to(stream)

def import_name(builtins, modulename, globals, locals, fromlist):
    try:
        import_ = builtins["__import__"]
    except KeyError:
        raise ImportError, "__import__ not found"
    return import_(modulename, globals, locals, fromlist)

def import_all_from(module, locals):
    try:
        all = module.__all__
    except AttributeError:
        try:
            dict = module.__dict__
        except AttributeError:
            raise ImportError, ("from-import-* object has no __dict__ "
                                "and no __all__")
        all = dict.keys()
        skip_leading_underscores = True
    else:
        skip_leading_underscores = False
    for name in all:
        if skip_leading_underscores and name[0]=='_':
            continue
        locals[name] = getattr(module, name)

def import_from(module, name):
    try:
        return getattr(module, name)
    except AttributeError:
        raise ImportError, "cannot import name '%s'" % name

def load_name(name, locals, globals, builtins):
    try:
        return locals[name]
    except KeyError:
        try:
            return globals[name]
        except KeyError:
            try:
                return builtins[name]
            except KeyError:
                raise NameError, "name '%s' is not defined" % name

def load_closure(locals, name):
    # this assumes that 'locals' is an extended dictionary with a
    # 'cell' method to explicitely access a cell
    return locals.cell(name)

def concatenate_arguments(args, extra_args):
    return args + tuple(extra_args)

def concatenate_keywords(kw, extra_kw):
    if not isinstance(extra_kw, dict):
        raise TypeError, "argument after ** must be a dictionary"
    result = kw.copy()
    for key, value in extra_kw.items():
        if key in result:
            # XXX fix error message
            raise TypeError, ("got multiple values "
                              "for keyword argument '%s'" % key)
        result[key] = value
    return result
