import subprocess, sys, shutil

class MissingDependenciesError(Exception):
    pass


cffi_build_scripts = {
    "sqlite3": "_sqlite3_build.py",
    "audioop": "_audioop_build.py",
    "tk": "_tkinter/tklib_build.py",
    "curses": "_curses_build.py" if sys.platform != "win32" else None,
    "syslog": "_syslog_build.py" if sys.platform != "win32" else None,
    "gdbm": "_gdbm_build.py"  if sys.platform != "win32" else None,
    "pwdgrp": "_pwdgrp_build.py" if sys.platform != "win32" else None,
    "xx": None,    # for testing: 'None' should be completely ignored
    }

def create_cffi_import_libraries(pypy_c, options, basedir):
    shutil.rmtree(str(basedir.join('lib_pypy', '__pycache__')),
                  ignore_errors=True)
    for key, module in sorted(cffi_build_scripts.items()):
        if module is None or getattr(options, 'no_' + key, False):
            continue
        if module.endswith('.py'):
            args = [str(pypy_c), module]
            cwd = str(basedir.join('lib_pypy'))
        else:
            args = [str(pypy_c), '-c', 'import ' + module]
            cwd = None
        print >> sys.stderr, '*', ' '.join(args)
        try:
            subprocess.check_call(args, cwd=cwd)
        except subprocess.CalledProcessError:
            print >>sys.stderr, """!!!!!!!!!!\nBuilding {0} bindings failed.
You can either install development headers package,
add the --without-{0} option to skip packaging this
binary CFFI extension, or say --without-cffi.""".format(key)
            raise MissingDependenciesError(module)

if __name__ == '__main__':
    import py
    if '__pypy__' not in sys.builtin_module_names:
        print 'Call with a pypy interpreter'
        sys.exit(-1)

    class Options(object):
        pass

    exename = py.path.local(sys.executable) 
    basedir = exename
    while not basedir.join('include').exists():
        _basedir = basedir.dirpath()
        if _basedir == basedir:
            raise ValueError('interpreter %s not inside pypy repo', 
                                 str(exename))
        basedir = _basedir
    options = Options()
    create_cffi_import_libraries(exename, options, basedir) 
