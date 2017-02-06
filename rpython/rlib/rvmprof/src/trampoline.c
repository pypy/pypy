#include "trampoline.h"

#include "machine.h"

#define _GNU_SOURCE
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/mman.h>
#include <dlfcn.h>
#include <errno.h>
#include <stdint.h>
#include <unistd.h>

#if __APPLE__
#include <mach-o/dyld.h>
#endif

#define PAGE_ALIGNED(a,size) (void*)(((uintptr_t)a) & ~(size - 1)) 

/*
 * The trampoline works the following way:
 *
 * `eval` is the traditional PyEval_EvalFrameEx (for 2.7)
 * `page` is allocated and used as memory block to execute
 *        the first few instructions from eval
 * `vmprof_eval` is a function just saving the
 *               frame in rbx
 *
 *          +--- eval ----------+
 *     +----| jmp vmprof_eval   | <-- patched, original bits moved to page
 *     | +->| asm instr 1       |
 *     | |  | asm instr 2       |
 *     | |  | ...               |
 *     | |  +-------------------+
 *     | |                          
 *     | |  +--- page ----------+<-+
 *     | |  | push rbp          | <-- copied from PyEval_Loop
 *     | |  | mov rsp -> rbp    |  |
 *     | |  | ...               |  |
 *     | |  | ...               |  |
 *     | +--| jmp eval+copied   |  |
 *     |    +-------------------+  |
 *     |                           |
 *     +--->+--- vmprof_eval ---+  |
 *          | ...               |  |
 *          | push rbx          |  |
 *          | mov rdi -> rbx    | <-- save the frame, custom method
 *          | call eval         |--+
 *          | ...               |
 *          | retq              |
 *          +-------------------+
 */

static
int g_patched = 0;

static char * g_trampoline = NULL;
// the machine code size copied over from the callee
static int g_trampoline_length;

void _jmp_to(char * a, uintptr_t addr, int call) {

    // TODO 32-bit

    // moveabsq <addr>, <reg>
    a[0] = 0x48; // REX.W
    if (call) {
        a[1] = 0xb8; // %rax
    } else {
        a[1] = 0xba; // %rdx
    }
    a[2] = addr & 0xff;
    a[3] = (addr >> 8) & 0xff;
    a[4] = (addr >> 16) & 0xff;
    a[5] = (addr >> 24) & 0xff;
    a[6] = (addr >> 32) & 0xff;
    a[7] = (addr >> 40) & 0xff;
    a[8] = (addr >> 48) & 0xff;
    a[9] = (addr >> 56) & 0xff;

    if (call) {
        a[10] = 0xff;
        a[11] = 0xd0;
    } else {
        a[10] = 0xff;
        a[11] = 0xe2;
    }
}

// a hilarious typo, tramp -> trump :)
int _redirect_trampoline_and_back(char * eval, char * trump, char * vmprof_eval) {

    char * trump_first_byte = trump;
    int needed_bytes = 12;
    int bytes = 0;
    char * ptr = eval;

    // 1) copy the instructions that should be redone in the trampoline
    while (bytes < needed_bytes) {
        unsigned int res = vmp_machine_code_instr_length(ptr);
        if (res == 0) {
            return 1;
        }
        bytes += res;
        ptr += res;
    }
    g_trampoline_length = bytes;

    // 2) initiate the first few instructions of the eval loop
    {
        (void)memcpy(trump, eval, bytes);
        _jmp_to(trump+bytes, (uintptr_t)eval+bytes, 0);
        //char * wptr = trump;
        //*wptr++ = 0x55;

        //*wptr++ = 0x48;
        //*wptr++ = 0x89;
        //*wptr++ = 0xe5;

        //*wptr++ = 0x53;
        //*wptr++ = 0x53;

        //*wptr++ = 0x48;
        //*wptr++ = 0x89;
        //*wptr++ = 0xfb;

        //char * trampcall = wptr;
        //wptr += 12;

        //// pop 
        //*wptr++ = 0x5b;
        //*wptr++ = 0x5b;
        //*wptr++ = 0x5d;
        //*wptr++ = 0xc3;

        //_jmp_to(trampcall, (uintptr_t)wptr, 1);

        //(void)memcpy(wptr, eval, bytes);
        //wptr += bytes;
        //_jmp_to(wptr, (uintptr_t)eval+bytes, 0);
    }

    // 3) overwrite the first few bytes of callee to jump to tramp
    // callee must call back 
    _jmp_to(eval, (uintptr_t)vmprof_eval, 0);

    return 0;
}


int vmp_patch_callee_trampoline(void * callee_addr, void * vmprof_eval, void ** vmprof_eval_target)
{
    int result;
    int pagesize;

    if (g_trampoline != NULL) {
        return 0; // already patched
    }

    pagesize = sysconf(_SC_PAGESIZE);
    errno = 0;

    result = mprotect(PAGE_ALIGNED(callee_addr, pagesize), pagesize*2, PROT_READ|PROT_WRITE);
    if (result != 0) {
        fprintf(stderr, "read|write protecting callee_addr\n");
        return -1;
    }
    // create a new page and set it all of it writable
    char * page = (char*)mmap(NULL, pagesize, PROT_READ|PROT_WRITE|PROT_EXEC,
                              MAP_ANON | MAP_PRIVATE, 0, 0);
    if (page == NULL) {
        return -1;
    }

    char * a = (char*)callee_addr;
    if (_redirect_trampoline_and_back(a, page, vmprof_eval) != 0) {
        return -1;
    }

    result = mprotect(PAGE_ALIGNED(callee_addr, pagesize), pagesize*2, PROT_READ|PROT_EXEC);
    if (result != 0) {
        fprintf(stderr, "read|exec protecting callee addr\n");
        return -1;
    }
    // revert, the page should not be writable any more now!
    result = mprotect((void*)page, pagesize, PROT_READ|PROT_EXEC);
    if (result != 0) {
        fprintf(stderr, "read|exec protecting tramp\n");
        return -1;
    }

    g_trampoline = page;
    *vmprof_eval_target = page;

    return 0;
}

int vmp_unpatch_callee_trampoline(void * callee_addr)
{
    return 0; // currently the trampoline is not removed

    //if (!g_patched) {
    //    return -1;
    //}

    //int result;
    //int pagesize = sysconf(_SC_PAGESIZE);
    //errno = 0;

    //result = mprotect(PAGE_ALIGNED(callee_addr, pagesize), pagesize*2, PROT_READ|PROT_WRITE);
    //if (result != 0) {
    //    fprintf(stderr, "read|write protecting callee_addr\n");
    //    return 1;
    //}

    //// copy back, assume everything is as if nothing ever happened!!
    //(void)memcpy(callee_addr, g_trampoline, g_trampoline_length);

    //result = mprotect(PAGE_ALIGNED(callee_addr, pagesize), pagesize*2, PROT_READ|PROT_EXEC);
    //if (result != 0) {
    //    fprintf(stderr, "read|exec protecting callee addr\n");
    //    return 1;
    //}

    //munmap(g_trampoline, pagesize);
    //g_trampoline = NULL;
    //g_trampoline_length = 0;

    //return 0;
}
