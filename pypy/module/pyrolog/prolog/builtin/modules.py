import py
from prolog.builtin.register import expose_builtin
from prolog.interpreter.term import Atom, Callable, Var, Term, Number
from prolog.interpreter import error
from prolog.builtin.sourcehelper import get_source
from prolog.interpreter import continuation
from prolog.interpreter.helper import is_term, unwrap_predicate_indicator
from prolog.interpreter.signature import Signature

meta_args = list("0123456789:?+-")
libsig = Signature.getsignature("library", 1)
andsig = Signature.getsignature(",", 2)

@expose_builtin("module", unwrap_spec=["atom", "list"])
def impl_module(engine, heap, name, exports):
    engine.modulewrapper.add_module(name, exports)

def handle_use_module_with_library(engine, heap, module, path, imports=None):
    import os
    import os.path
    from prolog.builtin.sourcehelper import get_filehandle
    newpath = None
    if path.signature().eq(libsig):
        arg = path.argument_at(0)
        if isinstance(arg, Var) or not isinstance(arg, Atom): # XXX throw different errors
            error.throw_instantiation_error()
        modulename = arg.name()
        assert modulename is not None
        for libpath in engine.modulewrapper.libs:
            temppath = os.path.join(libpath, modulename)
            try:
                assert isinstance(temppath, str)
                fd = get_filehandle(temppath)
            except OSError:
                continue
                assert 0, "unreachable"
            else:
                assert isinstance(fd, int)
                os.close(fd) # cleanup
                newpath = Atom(temppath)
                break
        if not newpath:
            error.throw_existence_error("source_sink", arg)
    else:
        error.throw_existence_error("source_sink", path)
    assert isinstance(newpath, Atom)
    handle_use_module(engine, heap, module, newpath, imports)

def handle_use_module(engine, heap, module, path, imports=None):
    m = engine.modulewrapper
    path = path.name()
    modulename = _basename(path)
    if path.endswith(".pl"):
        stop = len(modulename) - 3
        assert stop >= 0
        modulename = modulename[:stop]
    if modulename not in m.modules and modulename not in m.seen_modules: # prevent recursive imports
        m.seen_modules[modulename] = None
        current_module = m.current_module
        file_content = get_source(path)
        engine.runstring(file_content)
        for sig in m.current_module.exports:
            if sig not in m.current_module.functions:
                m.current_module = current_module
                error.throw_import_error(modulename, sig)
        module = m.current_module = current_module
        # XXX should use name argument of module here like SWI
    try:
        imported_module = m.modules[modulename]
    except KeyError: # we did not parse a correctly defined module file
        pass
    else:
        module.use_module(imported_module, imports)

@expose_builtin("use_module", unwrap_spec=["callable"], needs_module=True)
def impl_use_module(engine, heap, module, path):
    if isinstance(path, Atom):
        handle_use_module(engine, heap, module, path)
    else:
        handle_use_module_with_library(engine, heap, module, path)

@expose_builtin("use_module", unwrap_spec=["callable", "list"], needs_module=True)
def impl_use_module_with_importlist(engine, heap, module, path, imports):
    importlist = []
    for sigatom in imports:
        importlist.append(Signature.getsignature(
                *unwrap_predicate_indicator(sigatom))) 
    if isinstance(path, Atom):
        handle_use_module(engine, heap, module, path, importlist)
    else:
        handle_use_module_with_library(engine, heap, module, path, importlist)

@expose_builtin("module", unwrap_spec=["atom"])
def impl_module_1(engine, heap, name):
    engine.switch_module(name)

@expose_builtin(":", unwrap_spec=["atom", "callable"], 
        handles_continuation=True)
def impl_module_prefixing(engine, heap, modulename, 
        call, scont, fcont):
    module = engine.modulewrapper.get_module(modulename, call)
    return engine.call(call, module, scont, fcont, heap)

@expose_builtin("add_library_dir", unwrap_spec=["atom"])
def impl_add_library_dir(engine, heap, path):
    from os.path import isdir
    assert path is not None
    if not isdir(path):
        error.throw_existence_error("source_sink", Callable.build(path))
    libs = engine.modulewrapper.libs
    for lib in libs:
        if lib == path:  
            return
    engine.modulewrapper.libs.append(path)

@continuation.make_failure_continuation
def continue_librarydir(Choice, engine, scont, fcont, heap, pathvar, keycount):
    if keycount < len(engine.modulewrapper.libs) - 1:
        fcont = Choice(engine, scont, fcont, heap, pathvar, keycount + 1)
        heap = heap.branch()
    pathvar.unify(Callable.build(engine.modulewrapper.libs[keycount]), heap)
    return scont, fcont, heap

@expose_builtin("library_directory", unwrap_spec=["obj"],
        handles_continuation=True)
def impl_library_directory(engine, heap, directory, scont, fcont):
    if isinstance(directory, Var):
        if not engine.modulewrapper.libs:
            raise error.UnificationFailed
        return continue_librarydir(engine, scont, fcont, heap, directory, 0)
    elif isinstance(directory, Atom):
        for lib in engine.modulewrapper.libs:
            if lib == directory.name():
                return scont, fcont, heap
    raise error.UnificationFailed()

@expose_builtin("this_module", unwrap_spec=["obj"])
def impl_this_module(engine, heap, module):
    name = engine.modulewrapper.current_module.name
    Callable.build(name).unify(module, heap)  

@expose_builtin("meta_predicate", unwrap_spec=["callable"])
def impl_meta_predicate(engine, heap, predlist):
    run = True
    while run:
        assert isinstance(predlist, Callable)
        if predlist.signature().eq(andsig):
            pred = predlist.argument_at(0)
            predlist = predlist.argument_at(1)
            if isinstance(predlist, Var):
                error.throw_instantiation_error()
        else:
            pred = predlist
            run = False
        assert isinstance(pred, Callable)
        args = unwrap_meta_arguments(pred)
        engine.modulewrapper.current_module.add_meta_predicate(
                pred.signature(), args)
          
def unwrap_meta_arguments(predicate):
    assert isinstance(predicate, Callable)
    args = predicate.arguments()
    arglist = []
    for arg in args:
        if isinstance(arg, Var):
            error.throw_instantiation_error()
            assert 0
        elif isinstance(arg, Atom) and arg.name() in meta_args:
            val = arg.name()
        elif isinstance(arg, Number) and 0 <= arg.num <= 9:
            val = str(arg.num)
        else:
            error.throw_domain_error("expected one of 0..9, :, ?, +, -", arg)
            assert 0
        arglist.append(val[0])
    return "".join(arglist)

@continuation.make_failure_continuation
def continue_current_module(Choice, engine, scont, fcont, heap, allmods, i, modvar):
    if i < len(allmods) - 1:
        fcont = Choice(engine, scont, fcont, heap, allmods, i + 1, modvar)
        heap = heap.branch()
    modvar.unify(allmods[i], heap)
    return scont, fcont, heap

@expose_builtin("current_module", unwrap_spec=["obj"],
        handles_continuation=True)
def impl_current_module(engine, heap, module, scont, fcont):
    if isinstance(module, Atom):
        try:
            engine.modulewrapper.modules[module.name()]
        except KeyError:
            raise error.UnificationFailed()
    elif isinstance(module, Var):
        mods = [val.nameatom for val in
                    engine.modulewrapper.modules.values()]
        return continue_current_module(engine, scont, fcont, heap, mods, 0, module)
    else:
        raise error.UnificationFailed()
    return scont, fcont, heap

def _basename(path):
    index = path.rfind("/") + 1 # XXX OS specific
    if index == 0:
        return path
    assert index >= 0
    return path[index:]
