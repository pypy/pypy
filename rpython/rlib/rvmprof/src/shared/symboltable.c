#include "symboltable.h"

#include "vmprof.h"
#include "machine.h"

#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#include <dlfcn.h>
#ifdef VMPROF_LINUX
#include <link.h>
#endif

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

struct backtrace_state * bstate = NULL;
int vmp_resolve_addr(void * addr, char * name, int name_len, int * lineno, char * srcfile, int srcfile_len) {
#ifdef __APPLE__
    Dl_info info;
    if (dladdr((const void*)addr, &info) == 0) {
        return 1;
    }
    if (info.dli_sname != NULL) {
        (void)strncpy(name, info.dli_sname, name_len-1);
        name[name_len-1] = 0;
    }
    lookup_vmprof_debug_info(name, info.dli_fbase, srcfile, srcfile_len, lineno);
#elif defined(__unix__)
    if (bstate == NULL) {
        bstate = backtrace_create_state (NULL, 1, backtrace_error_cb, NULL);
    }
    addr_info_t info = { .name = name, .name_len = name_len,
                         .srcfile = srcfile, .srcfile_len = srcfile_len,
                         .lineno = lineno
                       };
    if (backtrace_pcinfo(bstate, (uintptr_t)addr, backtrace_full_cb,
                         backtrace_error_cb, (void*)&info)) {
        // failed
        return 1;
    }

    // nothing found, try with dladdr
    if (info.name[0] == 0) {
        Dl_info dlinfo;
        dlinfo.dli_sname = NULL;
        (void)dladdr((const void*)addr, &dlinfo);
        if (dlinfo.dli_sname != NULL) {
            (void)strncpy(info.name, dlinfo.dli_sname, info.name_len-1);
            name[name_len-1] = 0;
        }
    }
#endif
    return 0;
}

#ifdef RPYTHON_VMPROF

#define WORD_SIZE sizeof(long)
#define ADDR_SIZE sizeof(void*)
#define MAXLEN 1024

void _dump_native_symbol(int fileno, void * addr, char * sym, int linenumber, char * filename) {
    char natsym[64];
    off_t pos_before;
    struct str {
        void * addr;
        // NOTE windows 64, not supported yet
        long size;
        char str[1024];
    } s;
    pos_before = lseek(fileno, 0, SEEK_CUR);
    lseek(fileno, 0, SEEK_END);

    s.addr = addr;
    /* must mach '<lang>:<name>:<line>:<file>'
     * 'n' has been chosen as lang here, because the symbol
     * can be generated from several languages (e.g. C, C++, ...)
     */
    // MARKER_NATIVE_SYMBOLS is \x08
    write(fileno, "\x08", 1);
    if (sym == NULL || sym[0] == '\x00') {
        snprintf(natsym, 64, "<native symbol %p>", addr);
        sym = natsym;
    }
    if (filename != NULL) {
        s.size = snprintf(s.str, 1024, "n:%s:%d:%s", sym, linenumber, filename);
    } else {
        s.size = snprintf(s.str, 1024, "n:%s:%d:-", sym, linenumber);
    }
    write(fileno, &s, sizeof(void*)+sizeof(long)+s.size);

    lseek(fileno, pos_before, SEEK_SET);
}

int _skip_string(int fileno)
{
    long chars;
    int count = read(fileno, &chars, sizeof(long));
    LOG("reading string of %d chars\n", chars);
    if (count <= 0) {
        return 1;
    }
    lseek(fileno, chars, SEEK_CUR);

    return 0;
}

int _skip_header(int fileno, int * version, int * flags)
{
    unsigned char r[4];
    (void)read(fileno, r, 4);
    unsigned char count = r[3];
    *version = (r[0] & 0xff) << 8 | (r[1] & 0xff);
    *flags = r[2];
    lseek(fileno, (int)count, SEEK_CUR);
    return 0;
}

long _read_word(int fileno)
{
    long w;
    read(fileno, &w, WORD_SIZE);
    return w;
}

void * _read_addr(int fileno)
{
    void * a;
    read(fileno, &a, ADDR_SIZE);
    return a;
}

int _skip_word(int fileno)
{
    lseek(fileno, WORD_SIZE, SEEK_CUR);
    return 0;
}

int _skip_addr(int fileno)
{
    lseek(fileno, ADDR_SIZE, SEEK_CUR);
    return 0;
}

int _skip_time_and_zone(int fileno)
{
    lseek(fileno, sizeof(int64_t)*2 + 8, SEEK_CUR);
    return 0;
}


void dump_native_symbols(int fileno)
{
    // only call this function
    off_t orig_pos, cur_pos;
    char marker;
    ssize_t count;
    int version;
    int flags;
    int memory = 0, lines = 0, native = 0;
    orig_pos = lseek(fileno, 0, SEEK_CUR);

    lseek(fileno, 5*WORD_SIZE, SEEK_SET);

    while (1) {
        LOG("pre read\n");
        count = read(fileno, &marker, 1);
        LOG("post read\n");
        if (count <= 0) {
            break;
        }
        cur_pos = lseek(fileno, 0, SEEK_CUR);
        LOG("posss 0x%llx %d\n", cur_pos-1, cur_pos-1);
        switch (marker) {
            case MARKER_HEADER: {
                LOG("header 0x%llx\n", cur_pos);
                if (_skip_header(fileno, &version, &flags) != 0) {
                    return;
                }
                memory = (flags & PROFILE_MEMORY) != 0;
                native = (flags & PROFILE_NATIVE) != 0;
                lines = (flags & PROFILE_LINES) != 0;
                break;
            } case MARKER_META: {
                LOG("meta 0x%llx\n", cur_pos);
                if (_skip_string(fileno) != 0) { return; }
                if (_skip_string(fileno) != 0) { return; }
                break;
            } case MARKER_TIME_N_ZONE:
              case MARKER_TRAILER: {
                LOG("tnz or trailer 0x%llx\n", cur_pos);
                if (_skip_time_and_zone(fileno) != 0) { return; }
                break;
            } case MARKER_VIRTUAL_IP:
              case MARKER_NATIVE_SYMBOLS: {
                LOG("virtip 0x%llx\n", cur_pos);
                if (_skip_addr(fileno) != 0) { return; }
                if (_skip_string(fileno) != 0) { return; }
                break;
            } case MARKER_STACKTRACE: {
                long trace_count = _read_word(fileno);
                long depth = _read_word(fileno);

                LOG("stack 0x%llx %d %d\n", cur_pos, trace_count, depth);

                for (long i = depth/2-1; i >= 0; i--) {
                    long kind = (long)_read_addr(fileno);
                    void * addr = _read_addr(fileno);
                    if (kind == VMPROF_NATIVE_TAG) {
                        LOG("found kind %p\n", addr);
                        char name[MAXLEN];
                        char srcfile[MAXLEN];
                        name[0] = 0;
                        srcfile[0] = 0;
                        int lineno = 0;
                        if (vmp_resolve_addr(addr, name, MAXLEN, &lineno, srcfile, MAXLEN) == 0) {
                            LOG("dumping add %p, name %s, %s:%d\n", addr, name, srcfile, lineno);
                            _dump_native_symbol(fileno, addr, name, lineno, srcfile);
                        }
                    }
                }
                LOG("passed  memory %d \n", memory);

                if (_skip_addr(fileno) != 0) { return; } // thread id
                if (memory) {
                    if (_skip_addr(fileno) != 0) { return; } // profile memory
                }

                break;
            } default: {
                fprintf(stderr, "unknown marker 0x%x\n", marker);
                return;
            }
        }

        cur_pos = lseek(fileno, 0, SEEK_CUR);
        if (cur_pos >= orig_pos) {
            break;
        }
    }

    lseek(fileno, 0, SEEK_END);
}
#endif
