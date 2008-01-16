import py
import os, sys


def compile_so_file():
    from distutils.dist import Distribution
    from distutils.extension import Extension
    from distutils.ccompiler import get_default_compiler
    udir = py.test.ensuretemp('_ctypes_test')
    cfile = py.magic.autopath().dirpath().join("_ctypes_test.c")
    saved_environ = os.environ.items()
    olddir = udir.chdir()
    try:
        attrs = {
            'name': "_ctypes_test",
            'ext_modules': [
                Extension("_ctypes_test", [str(cfile)]),
                ],
            'script_name': 'setup.py',
            'script_args': ['-q', 'build_ext', '--inplace'],
            }
        dist = Distribution(attrs)
        if not dist.parse_command_line():
            raise ValueError, "distutils cmdline parse error"
        dist.run_commands()
    finally:
        olddir.chdir()
        for key, value in saved_environ:
            if os.environ.get(key) != value:
                os.environ[key] = value

    if sys.platform == 'win32':
        so_ext = '.dll'
    else:
        so_ext = '.so'
    return udir.join('_ctypes_test' + so_ext)


sofile = compile_so_file()
