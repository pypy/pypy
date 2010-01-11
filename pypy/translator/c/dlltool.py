
from pypy.translator.driver import TranslationDriver
from pypy.translator.c.genc import CLibraryBuilder, CCompilerDriver
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.tool.cbuild import ExternalCompilationInfo

class DLLDef(object):
    def __init__(self, name, functions=[], policy=None, config=None):
        self.name = name
        self.functions = functions # [(function, annotation), ...]
        self.driver = TranslationDriver(config=config)
        self.driver.setup_library(self, policy=policy)

    def compile(self):
        self.driver.proceed(['compile_c'])
        return self.driver.cbuilder.so_name

    def getcbuilder(self, translator, config):
        bk = translator.annotator.bookkeeper
        entrypoints = {}
        for f, _ in self.functions:
            graph = bk.getdesc(f).cachedgraph(None)
            entrypoints[f.func_name] = getfunctionptr(graph)

        return CLibraryBuilder(translator, entrypoints, config)
