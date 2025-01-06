#include "symboltable.h"

#include "vmprof.h"
#include "machine.h"

#include "khash.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include <assert.h>
#include <dlfcn.h>

#if defined(VMPROF_LINUX)
#include <link.h>
#if defined(X86_64) || defined(X86_32)
#include "unwind/vmprof_unwind.h"
static const char * vmprof_error = NULL;
static void * libhandle = NULL;

static void* unw_local_address_space = NULL;
// function copied from libunwind using dlopen
static int (*unw_get_proc_name_by_ip)(void *, unw_word_t, char *, size_t, unw_word_t *, void *) = NULL;
#endif
#endif
static int resolve_with_libunwind = 0;

#ifdef _PY_TEST
#define LOG(...) printf(__VA_ARGS__)
#else
#define LOG(...)
#endif

#ifdef __APPLE__

#include <mach-o/loader.h>
#include <mach-o/nlist.h>
#include <mach-o/stab.h>
#include <mach-o/dyld.h>
#include <mach-o/dyld_images.h>
#include <mach-o/fat.h>

int dyld_index_for_hdr(const struct mach_header_64 * hdr)
{
    const struct mach_header_64 * it;
    int image_count = _dyld_image_count();
    for (int i = 0; i < image_count; i++) {
        it = (const struct mach_header_64*)_dyld_get_image_header(i);
        if (it == hdr) {
            return i;
        }
    }

    return -1;
}

void lookup_vmprof_debug_info(const char * name, const void * h,
                              char * srcfile, int srcfile_len, int * lineno) {

    const struct mach_header_64 * hdr = (const struct mach_header_64*)h;
    const struct symtab_command *sc;
    const struct load_command *lc;

    int index = dyld_index_for_hdr(hdr);
    intptr_t slide = _dyld_get_image_vmaddr_slide(index);
    if (hdr->magic != MH_MAGIC_64) {
        return;
    }

    if (hdr->cputype != CPU_TYPE_X86_64) {
        return;
    }

    lc = (const struct load_command *)(hdr + 1);

    struct segment_command_64 * __linkedit = NULL;
    struct segment_command_64 * __text = NULL;

    LOG(" mach-o hdr has %d commands\n", hdr->ncmds);
    for (uint32_t j = 0; j < hdr->ncmds; j++, (lc = (const struct load_command *)((char *)lc + lc->cmdsize))) {
        if (lc->cmd == LC_SEGMENT_64) {
            struct segment_command_64 * sc = (struct segment_command_64*)lc;
            //LOG("segment command %s %llx %llx foff %llx fsize %llx\n",
            //    sc->segname, sc->vmaddr, sc->vmsize, sc->fileoff, sc->filesize);
            if (strncmp("__LINKEDIT", sc->segname, 16) == 0) {
                //LOG("segment command %s\n", sc->segname);
                __linkedit = sc;
            }
            if (strncmp("__TEXT", sc->segname, 16) == 0) {
                __text = sc;
            }
        }
    }

    if (__linkedit == NULL) {
        LOG("couldn't find __linkedit\n");
        return;
    } else if (__text == NULL) {
        LOG("couldn't find __text\n");
        return;
    }

    uint64_t fileoff = __linkedit->fileoff;
    uint64_t vmaddr = __linkedit->vmaddr;
    const char * baseaddr = (const char*) vmaddr + slide - fileoff;
    const char * __text_baseaddr = (const char*) slide - __text->fileoff;
    //LOG("%llx %llx %llx\n", slide, __text->vmaddr, __text->fileoff);
    const char * path = NULL;
    const char * filename = NULL;
    uint32_t src_line = 0;

    lc = (const struct load_command *)(hdr + 1);
    for (uint32_t j = 0; j < hdr->ncmds; j++, (lc = (const struct load_command *)((char *)lc + lc->cmdsize))) {
        if (lc->cmd == LC_SYMTAB) {
            LOG(" cmd %d/%d is LC_SYMTAB\n", j, hdr->ncmds);
            sc = (const struct symtab_command*) lc;
            // skip if symtab entry is not populated
            if (sc->symoff == 0) {
                LOG("LC_SYMTAB.symoff == 0\n");
                continue;
            } else if (sc->stroff == 0) {
                LOG("LC_SYMTAB.stroff == 0\n");
                continue;
            } else if (sc->nsyms == 0) {
                LOG("LC_SYMTAB.nsym == 0\n");
                continue;
            } else if (sc->strsize == 0) {
                LOG("LC_SYMTAB.strsize == 0\n");
                continue;
            }
            const char * strtbl = (const char*)(baseaddr + sc->stroff);
            struct nlist_64 * l = (struct nlist_64*)(baseaddr + sc->symoff);
            //LOG("baseaddr %llx fileoff: %lx vmaddr %llx, symoff %llx stroff %llx slide %llx %d\n",
            //        baseaddr, fileoff, vmaddr, sc->symoff, sc->stroff, slide, sc->nsyms);
            for (uint32_t s = 0; s < sc->nsyms; s++) {
                struct nlist_64 * entry = &l[s];
                uint32_t t = entry->n_type;
                bool is_debug = (t & N_STAB) != 0;
                if (!is_debug) {
                    continue;
                }
                uint32_t off = entry->n_un.n_strx;
                if (off >= sc->strsize || off == 0) {
                    continue;
                }
                const char * sym = &strtbl[off];
                if (sym[0] == '\x00') {
                    sym = NULL;
                }
                // switch through the  different types
                switch (t) {
                    case N_FUN: {
                        if (sym != NULL && strcmp(name, sym+1) == 0) {
                            *lineno = src_line;
                            if (src_line == 0) {
                                *lineno = entry->n_desc;
                            }
                            snprintf(srcfile, srcfile_len, "%s%s", path, filename);
                        }
                        break;
                    }
                    case N_SLINE: {
                        // does not seem to occur
                        src_line = entry->n_desc;
                        break;
                    }
                    case N_SO: {
                        // the first entry is the path, the second the filename,
                        // if a null occurs, the path and filename is reset
                        if (sym == NULL) {
                            path = NULL;
                            filename = NULL;
                        } else if (path == NULL) {
                            path = sym;
                        } else if (filename == NULL) {
                            filename = sym;
                        }
                        break;
                    }
                }
            }
        }
    }
}

#endif

// copied from vmp_stack.c
#ifdef VMPROF_LINUX
#define LIBUNWIND "libunwind.so"
#ifdef __i386__
#define PREFIX "x86"
#define LIBUNWIND_SUFFIX ""
#elif __x86_64__
#define PREFIX "x86_64"
#define LIBUNWIND_SUFFIX "-x86_64"
#endif
#define U_PREFIX "_U"
#define UL_PREFIX "_UL"
#endif

#ifdef VMPROF_LINUX
int vmp_load_libunwind(void) {
    void * oldhandle = NULL;
    struct link_map * map = NULL;
    if (libhandle == NULL) {
        // on linux, the wheel includes the libunwind shared object.
        libhandle = dlopen(NULL, RTLD_NOW);
        if (libhandle != NULL) {
            // load the link map, it will contain an entry to
            // .libs_vmprof/libunwind-...so, this is the file that is
            // distributed with the wheel.
            if (dlinfo(libhandle, RTLD_DI_LINKMAP, &map) != 0) {
                (void)dlclose(libhandle);
                libhandle = NULL;
                goto bail_out;
            }
            // grab the new handle
            do {
                if (strstr(map->l_name, ".libs_vmprof/libunwind" LIBUNWIND_SUFFIX) != NULL) {
                    oldhandle = libhandle;
                    libhandle = dlopen(map->l_name, RTLD_LAZY|RTLD_LOCAL);
                    (void)dlclose(oldhandle);
                    oldhandle = NULL;
                    goto loaded_libunwind;
                }
                map = map->l_next;
            } while (map != NULL);
            // did not find .libs_vmprof/libunwind...
            (void)dlclose(libhandle);
            libhandle = NULL;
        }

        // fallback! try to load the system's libunwind.so
        if ((libhandle = dlopen(LIBUNWIND, RTLD_LAZY | RTLD_LOCAL)) == NULL) {
            printf("couldnt open %s \n", LIBUNWIND);
            goto bail_out;
        }
loaded_libunwind:
        if ((unw_get_proc_name_by_ip = dlsym(libhandle, UL_PREFIX PREFIX "_get_proc_name_by_ip")) == NULL) { // _ULx86_64_get_proc_name_by_ip
            printf("couldnt load %s \n", UL_PREFIX PREFIX "_get_proc_name_by_ip");
            goto bail_out;
        }
        if ((unw_local_address_space = dlsym(libhandle, UL_PREFIX PREFIX "_local_addr_space")) == NULL) { // _ULx86_64_local_addr_space
            printf("couldnt load %s \n", UL_PREFIX PREFIX "_local_addr_space");
            goto bail_out;
        }
        resolve_with_libunwind = 1;
    }
    return 1;

bail_out:
    vmprof_error = dlerror();
    fprintf(stderr, "could not load libunwind at runtime. error: %s\n", vmprof_error);
    resolve_with_libunwind = 0;
    return 0;
}


void vmp_close_libunwind(void) {

    if (libhandle != NULL) {
        if (dlclose(libhandle)) {
            vmprof_error = dlerror();
#if DEBUG
            fprintf(stderr, "could not close libunwind at runtime. error: %s\n", vmprof_error);
#endif
        }
        resolve_with_libunwind = 0;
        libhandle = NULL;
    }
}
#endif


#ifdef __unix__
#include "libbacktrace/backtrace.h"
void backtrace_error_cb(void *data, const char *msg, int errnum)
{
}

// a struct that helps to copy over data for the callbacks
typedef struct addr_info {
    char * name;
    int name_len;
    char * srcfile;
    int srcfile_len;
    int * lineno;
} addr_info_t;

int backtrace_full_cb(void *data, uintptr_t pc, const char *filename,
                      int lineno, const char *function)
{
    addr_info_t * info = (addr_info_t*)data;
    if (function != NULL) {
        // found the symbol name
        (void)strncpy(info->name, function, info->name_len);
    }
    if (filename != NULL) {
        (void)strncpy(info->srcfile, filename, info->srcfile_len);
    }
    *info->lineno = lineno;
    return 0;
}
#endif

int _vmp_resolve_addr_libunwind(void * addr, char * name, int name_len, int * lineno, char * srcfile, int srcfile_len) {

#if defined(X86_64) 

    uint64_t local_addr_space_addr = 0;

    asm(
        "mov %1, %%rax \n\t"
        "mov (%%rax), %0"
        : "=r" (local_addr_space_addr)
        : "r" (unw_local_address_space)
    );

#elif defined(x86_32)

    uint32_t local_addr_space_addr = 0;

    asm(
        "mov %1, %%eax \n\t"
        "mov (%%eax), %0"
        : "=r" (local_addr_space_addr)
        : "r" (unw_local_address_space)
    );

#endif
    
    if (resolve_with_libunwind == 0) {
        // unw_get_proc_name_by_ip hasn't been loaded => dont try to use it
        return 1;
    }

    unw_word_t offset = 0;

    int res_funcname = unw_get_proc_name_by_ip((void *) local_addr_space_addr, (unw_word_t) addr, name, name_len, &offset, NULL);
    
    if(res_funcname == 0) {
        return 0;
    }
    return 1;
}

static
struct backtrace_state * bstate = NULL;

int vmp_resolve_addr(void * addr, char * name, int name_len, int * lineno, char * srcfile, int srcfile_len) {
#ifdef __APPLE__
    Dl_info dlinfo;
    if (dladdr((const void*)addr, &dlinfo) == 0) {
        return 1;
    }
    if (dlinfo.dli_sname != NULL) {
        (void)strncpy(name, dlinfo.dli_sname, name_len-1);
        name[name_len-1] = 0;
    }
    lookup_vmprof_debug_info(name, dlinfo.dli_fbase, srcfile, srcfile_len, lineno);
    // copy the shared object name to the source file name if source cannot be determined
    if (srcfile[0] == 0 && dlinfo.dli_fname != NULL) {
        (void)strncpy(srcfile, dlinfo.dli_fname, srcfile_len-1);
        srcfile[srcfile_len-1] = 0;
    }
#elif defined(VMPROF_LINUX)
    if (bstate == NULL) {
        bstate = backtrace_create_state (NULL, 1, backtrace_error_cb, NULL);
    }
    addr_info_t info = { .name = name, .name_len = name_len,
                         .srcfile = srcfile, .srcfile_len = srcfile_len,
                         .lineno = lineno
                       };
    if (backtrace_pcinfo(bstate, (uintptr_t)addr, backtrace_full_cb,
                         backtrace_error_cb, (void*)&info)) {
        return _vmp_resolve_addr_libunwind(addr, name, name_len, lineno, srcfile, srcfile_len); 
        // failed
        //return 1;
    }

    // nothing found, try with dladdr
    if (info.name[0] == 0) {
        Dl_info dlinfo;
        dlinfo.dli_sname = NULL;
        (void)dladdr((const void*)addr, &dlinfo);
        if (dlinfo.dli_sname != NULL) {
            (void)strncpy(info.name, dlinfo.dli_sname, info.name_len-1);
            name[name_len-1] = 0;
        } else {
            // dladdr didn't find the name
            _vmp_resolve_addr_libunwind(addr, name, name_len, lineno, srcfile, srcfile_len);
        }
    }

    // copy the shared object name to the source file name if source cannot be determined
    if (srcfile[0] == 0) {
        Dl_info dlinfo;
        dlinfo.dli_fname = NULL;
        (void)dladdr((const void*)addr, &dlinfo);
        if (dlinfo.dli_fname != NULL) {
            (void)strncpy(srcfile, dlinfo.dli_fname, srcfile_len-1);
            srcfile[srcfile_len-1] = 0;
        }
    }
#endif
    return 0;
}
