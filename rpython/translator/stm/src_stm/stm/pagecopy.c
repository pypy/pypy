/* Imported by rpython/translator/stm/import_stmgc.py */

#define PAGECOPY_128(dest, src)                                         \
        asm volatile("movdqa (%0), %%xmm0\n"                            \
                     "movdqa 16(%0), %%xmm1\n"                          \
                     "movdqa 32(%0), %%xmm2\n"                          \
                     "movdqa 48(%0), %%xmm3\n"                          \
                     "movdqa %%xmm0, (%1)\n"                            \
                     "movdqa %%xmm1, 16(%1)\n"                          \
                     "movdqa %%xmm2, 32(%1)\n"                          \
                     "movdqa %%xmm3, 48(%1)\n"                          \
                     "movdqa 64(%0), %%xmm0\n"                          \
                     "movdqa 80(%0), %%xmm1\n"                          \
                     "movdqa 96(%0), %%xmm2\n"                          \
                     "movdqa 112(%0), %%xmm3\n"                         \
                     "movdqa %%xmm0, 64(%1)\n"                          \
                     "movdqa %%xmm1, 80(%1)\n"                          \
                     "movdqa %%xmm2, 96(%1)\n"                          \
                     "movdqa %%xmm3, 112(%1)\n"                         \
                     :                                                  \
                     : "r"(src), "r"(dest)                              \
                     : "xmm0", "xmm1", "xmm2", "xmm3", "memory")

static void pagecopy(void *dest, const void *src)
{
    unsigned long i;
    for (i = 0; i < 4096 / 128; i++) {
        PAGECOPY_128(dest + 128*i, src + 128*i);
    }
}

#if 0
static void pagecopy_256(void *dest, const void *src)
{
    PAGECOPY_128(dest,       src      );
    PAGECOPY_128(dest + 128, src + 128);
}
#endif

#if 0   /* XXX enable if detected on the cpu */
static void pagecopy_ymm8(void *dest, const void *src)
{
    asm volatile("0:\n"
                 "vmovdqa (%0), %%ymm0\n"
                 "vmovdqa 32(%0), %%ymm1\n"
                 "vmovdqa 64(%0), %%ymm2\n"
                 "vmovdqa 96(%0), %%ymm3\n"
                 "vmovdqa 128(%0), %%ymm4\n"
                 "vmovdqa 160(%0), %%ymm5\n"
                 "vmovdqa 192(%0), %%ymm6\n"
                 "vmovdqa 224(%0), %%ymm7\n"
                 "addq $256, %0\n"
                 "vmovdqa %%ymm0, (%1)\n"
                 "vmovdqa %%ymm1, 32(%1)\n"
                 "vmovdqa %%ymm2, 64(%1)\n"
                 "vmovdqa %%ymm3, 96(%1)\n"
                 "vmovdqa %%ymm4, 128(%1)\n"
                 "vmovdqa %%ymm5, 160(%1)\n"
                 "vmovdqa %%ymm6, 192(%1)\n"
                 "vmovdqa %%ymm7, 224(%1)\n"
                 "addq $256, %1\n"
                 "cmpq %2, %0\n"
                 "jne 0b"
                 : "=r"(src), "=r"(dest)
                 : "r"((char *)src + 4096), "0"(src), "1"(dest)
                 : "xmm0", "xmm1", "xmm2", "xmm3",
                   "xmm4", "xmm5", "xmm6", "xmm7");
}
#endif
