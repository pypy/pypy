
from rpython.translator.c.genc import CBuilder
from rpython.rtyper.typesystem import getfunctionptr
from rpython.translator.tool.cbuild import ExternalCompilationInfo


class CLibraryBuilder(CBuilder):
    standalone = False
    split = True

    def __init__(self, *args, **kwds):
        self.functions = kwds.pop('functions')
        self.name = kwds.pop('name')
        CBuilder.__init__(self, *args, **kwds)

    def getentrypointptr(self):
        entrypoints = []
        bk = self.translator.annotator.bookkeeper
        for f, _ in self.functions:
            graph = bk.getdesc(f).getuniquegraph()
            entrypoints.append(getfunctionptr(graph))
        return entrypoints

    def gen_makefile(self, targetdir, exe_name=None,
                    headers_to_precompile=[]):
        pass # XXX finish

    def compile(self):
        export_symbols = ([self.db.get(ep) for ep in self.getentrypointptr()] +
                          ['RPython_StartupCode'])
        extsymeci = ExternalCompilationInfo(export_symbols=export_symbols)
        self.eci = self.eci.merge(extsymeci)
        files = [self.c_source_filename] + self.extrafiles
        files += self.eventually_copy(self.eci.separate_module_files)
        self.eci.separate_module_files = ()
        oname = self.name
        self.so_name = self.translator.platform.compile(files, self.eci,
                                                        standalone=False,
                                                        outputfilename=oname)

    def get_entry_point(self, isolated=False):
        return self.so_name

