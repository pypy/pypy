#include "machine.h"

#include "_vmprof.h"
#include <stdio.h>

int vmp_machine_bits(void)
{
    return sizeof(void*)*8;
}

const char * vmp_machine_os_name(void)
{
#ifdef _WIN32
   #ifdef _WIN64
      return "win64";
   #endif
  return "win32";
#elif __APPLE__
    #include "TargetConditionals.h"
    #if TARGET_OS_MAC
        return "mac os x";
    #endif
#elif __linux__
    return "linux";
#else
    #error "Unknown compiler"
#endif
}

#ifdef VMP_SUPPORTS_NATIVE_PROFILING
#include "libudis86/udis86.h"
unsigned int vmp_machine_code_instr_length(char* pc)
{
    struct ud u;
    ud_init(&u);
    ud_set_input_buffer(&u, (uint8_t*)pc, 12);
    ud_set_mode(&u, vmp_machine_bits());
    return ud_decode(&u);
}
#endif
