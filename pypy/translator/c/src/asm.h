
/* optional assembler bits */
#if defined(__GNUC__) && defined(__i386__)
#  include "src/asm_gcc_x86.h"
#endif

#if defined(__GNUC__) && defined(__amd64__)
#  include "src/asm_gcc_x86_64.h"
#endif

#if defined(__GNUC__) && defined(__ppc__)
#  include "src/asm_ppc.h"
#endif
