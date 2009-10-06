
from pypy.translator.driver import TranslationDriver
from pypy.translator.c.genc import CBuilder, CCompilerDriver
from pypy.rpython.typesystem import getfunctionptr
from pypy.translator.tool.cbuild import ExternalCompilationInfo

class CLibraryBuilder(CBuilder):
    standalone = False
    split = True

    def __init__(self, *args, **kwds):
        self.functions = kwds.pop('functions')
        self.name = kwds.pop('name')
        CBuilder.__init__(self, *args, **kwds)

    def getentrypointptr(self):
        bk = self.translator.annotator.bookkeeper
        graphs = [bk.getdesc(f).cachedgraph(None) for f, _ in self.functions]
        return [getfunctionptr(graph) for graph in graphs]

    def gen_makefile(self, targetdir):
        pass # XXX finish

    def compile(self):
        export_symbols = ([self.db.get(ep) for ep in self.getentrypointptr()] +
                          ['RPython_StartupCode'])
        extsymeci = ExternalCompilationInfo(export_symbols=export_symbols)
        self.eci = self.eci.merge(extsymeci)
        files = [self.c_source_filename] + self.extrafiles
        oname = self.name
        self.so_name = self.translator.platform.compile(files, self.eci,
                                                        standalone=False,
                                                        outputfilename=oname)

    def get_entry_point(self, isolated=False):
        return self.so_name

class DLLDef(object):
    def __init__(self, name, functions=[], policy=None, config=None):
        self.name = name
        self.functions = functions # [(function, annotation), ...]
        self.driver = TranslationDriver(config=config)
        self.driver.setup_library(self, policy=policy)

    def compile(self):
        self.driver.proceed(['compile_c'])
        return self.driver.c_entryp

    def getcbuilder(self, translator, config):
        return CLibraryBuilder(translator, None, config,
                               functions=self.functions, name=self.name)
