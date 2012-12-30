
#if   defined(_M_IX86)
#include "switch_x86_msvc.h" /* MS Visual Studio on X86 */
#elif defined(_M_X64)
#include "switch_x64_msvc.h" /* MS Visual Studio on X64 */
#elif defined(__GNUC__) && defined(__amd64__)
#include "switch_x86_64_gcc.h" /* gcc on amd64 */
#elif defined(__GNUC__) && defined(__i386__)
#include "switch_x86_gcc.h" /* gcc on X86 */
#else
#error "Unsupported platform!"
#endif
