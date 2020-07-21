import py, sys, subprocess

currpath = py.path.local(__file__).dirpath()


def setup_make(targetname):
    if sys.platform == 'win32':
        py.test.skip('Cannot run this Makefile on windows')
    from rpython.translator.platform import platform as compiler
    compiler.execute_makefile(currpath, [targetname])
