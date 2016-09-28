import sys, shutil
from rpython.tool.runsubprocess import run_subprocess

class MissingDependenciesError(Exception):
    pass


cffi_build_scripts = {
    "sqlite3": "_sqlite3_build.py",
    "audioop": "_audioop_build.py",
    "tk": "_tkinter/tklib_build.py",
    "curses": "_curses_build.py" if sys.platform != "win32" else None,
    "syslog": "_syslog_build.py" if sys.platform != "win32" else None,
    "_gdbm": "_gdbm_build.py"  if sys.platform != "win32" else None,
    "pwdgrp": "_pwdgrp_build.py" if sys.platform != "win32" else None,
    "resource": "_resource_build.py" if sys.platform != "win32" else None,
    "lzma": "_lzma_build.py",
    "_decimal": "_decimal_build.py",
    "xx": None,    # for testing: 'None' should be completely ignored
    }

def create_cffi_import_libraries(pypy_c, options, basedir):
    shutil.rmtree(str(basedir.join('lib_pypy', '__pycache__')),
                  ignore_errors=True)
    failures = []
    for key, module in sorted(cffi_build_scripts.items()):
        if module is None or getattr(options, 'no_' + key, False):
            continue
        if module.endswith('.py'):
            args = [module]
            cwd = str(basedir.join('lib_pypy'))
        else:
            args = ['-c', 'import ' + module]
            cwd = None
        print >> sys.stderr, '*', ' '.join(args)
        try:
            status, stdout, stderr = run_subprocess(str(pypy_c), args, cwd=cwd)
            if status != 0:
                print >> sys.stderr, stdout, stderr
                failures.append((key, module))
        except:
            import traceback;traceback.print_exc()
            failures.append((key, module))
    return failures

if __name__ == '__main__':
    # NOTE: it does not work to execute this file to rebuild the cffi backends
    # for pypy3. This script is python 2! Thus you can specify
    # exefile as an argument to still be able to run this script with a pypy2 vm
    import py, os, argparse
    if '__pypy__' not in sys.builtin_module_names:
        print 'Call with a pypy interpreter'
        sys.exit(-1)

    class Options(object):
        pass

    parser = argparse.ArgumentParser(description='Build all cffi backends in lib_pypy')
    parser.add_argument('--exefile', dest='exefile', default=sys.executable,
                        help='instead of executing sys.executable' \
                             ' you can specify an alternative pypy vm here')
    args = parser.parse_args()

    exename = py.path.local(args.exefile)
    basedir = exename

    while not basedir.join('include').exists():
        _basedir = basedir.dirpath()
        if _basedir == basedir:
            raise ValueError('interpreter %s not inside pypy repo', 
                                 str(exename))
        basedir = _basedir
    options = Options()
    print >> sys.stderr, "There should be no failures here"
    failures = create_cffi_import_libraries(exename, options, basedir)
    if len(failures) > 0:
        print 'failed to build', [f[1] for f in failures]
        assert False

    # monkey patch a failure, just to test
    print >> sys.stderr, 'This line should be followed by a traceback'
    for k in cffi_build_scripts:
        setattr(options, 'no_' + k, True)
    must_fail = '_missing_build_script.py'
    assert not os.path.exists(str(basedir.join('lib_pypy').join(must_fail)))
    cffi_build_scripts['should_fail'] = must_fail
    failures = create_cffi_import_libraries(exename, options, basedir)
    assert len(failures) == 1
