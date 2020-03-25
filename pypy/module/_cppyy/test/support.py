import py, sys, subprocess

currpath = py.path.local(__file__).dirpath()


def setup_make(targetname):
    from rpython.translator.platform import platform as compiler
    compiler.execute_makefile(currpath, [targetname])
