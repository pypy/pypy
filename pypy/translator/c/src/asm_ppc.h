
void LL_flush_icache(long base, long size);

#ifndef PYPY_NOT_MAIN_FILE

#define __dcbst(base, index)    \
  __asm__ ("dcbst %0, %1" : /*no result*/ : "b%" (index), "r" (base) : "memory")
#define __icbi(base, index)    \
  __asm__ ("icbi %0, %1" : /*no result*/ : "b%" (index), "r" (base) : "memory")
#define __sync() __asm__ volatile ("sync")
#define __isync()       \
  __asm__ volatile ("isync")

void
LL_flush_icache(long base, long size)
{
	long i;

	for (i = 0; i < size; i += 32){
		__dcbst(base, i);
	}
	__sync();
	for (i = 0; i < size; i += 32){
		__icbi(base, i);
	}
	__isync();
}

#endif
