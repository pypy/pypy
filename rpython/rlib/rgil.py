import py
from rpython.conftest import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo

# these functions manipulate directly the GIL, whose definition does not
# escape the C code itself
translator_c_dir = py.path.local(cdir)

eci = ExternalCompilationInfo(
    includes = ['src/thread.h'],
    separate_module_files = [translator_c_dir / 'src' / 'thread.c'],
    include_dirs = [translator_c_dir],
    export_symbols = ['RPyGilYieldThread', 'RPyGilRelease',
                      'RPyGilAcquire', 'RPyFetchFastGil'])


gil_yield_thread  = llexternal('RPyGilYieldThread', [], lltype.Void,
                               _nowrapper=True, sandboxsafe=True,
                               compilation_info=eci)

gil_release       = llexternal('RPyGilRelease', [], lltype.Void,
                               _nowrapper=True, sandboxsafe=True,
                               compilation_info=eci)

gil_acquire       = llexternal('RPyGilAcquire', [], lltype.Void,
                              _nowrapper=True, sandboxsafe=True,
                              compilation_info=eci)

gil_fetch_fastgil = llexternal('RPyFetchFastGil', [], llmemory.Address,
                               _nowrapper=True, sandboxsafe=True,
                               compilation_info=eci)
