"""
Support for generating a perf map in /tmp/perf-PID.map
"""

from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

eci = ExternalCompilationInfo(separate_module_sources = [r"""
#include <unistd.h>
#include <stdio.h>

FILE *pypy_perf_map_file = NULL;

RPY_EXPORTED void perf_map_write_entry(
          const char *name,
          size_t start_addr,
          size_t end_addr) {

    if (!pypy_perf_map_file) {
        char pmap_filename[100];
        snprintf(pmap_filename, 100, "/tmp/perf-%d.map", getpid());
        pypy_perf_map_file = fopen(pmap_filename, "w");
    }

    fprintf(pypy_perf_map_file, "%lx %lx %s\n", start_addr,
            end_addr - start_addr, name);
    fflush(pypy_perf_map_file);
}
"""])

_perf_map_write_entry = rffi.llexternal(
    'perf_map_write_entry',
    [rffi.CCHARP , lltype.Unsigned, lltype.Unsigned], lltype.Void,
    compilation_info=eci,
    _nowrapper=True, transactionsafe=True)

# ____________________________________________________________

def write_perf_map_entry(name, start_addr, end_addr):
    # XXX: should be a profagent
    with rffi.scoped_str2charp("JIT: " + name) as loopname:
        _perf_map_write_entry(loopname, start_addr, end_addr)
