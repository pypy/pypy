import autopath, sys, os
from pypy.rpython.lltype import *
from pypy.translator.translator import Translator
from pypy.translator.c.database import LowLevelDatabase
from pypy.translator.c.genc import gen_source
from pypy.objspace.flow.model import Constant, Variable, SpaceOperation
from pypy.objspace.flow.model import Block, Link, FunctionGraph
from pypy.tool.udir import udir
from pypy.translator.tool.buildpyxmodule import make_module_from_c
from pypy.translator.gensupp import uniquemodulename


def compile_db(db):
    modulename = uniquemodulename('testing')
    targetdir = udir.join(modulename).ensure(dir=1)
    gen_source(db, modulename, str(targetdir))
    make_module_from_c(targetdir.join(modulename+'.c'),
                       include_dirs = [os.path.dirname(autopath.this_dir)])


def test_untyped_func():
    def f(x):
        return x+1
    t = Translator(f)
    graph = t.getflowgraph()

    F = FuncType([GcPtr(PyObject)], GcPtr(PyObject))
    S = GcStruct('testing', ('fptr', NonGcPtr(F)))
    f = functionptr(F, "f", graph=graph)
    s = malloc(S)
    s.fptr = f
    db = LowLevelDatabase()
    db.get(s)
    db.complete()
    compile_db(db)
