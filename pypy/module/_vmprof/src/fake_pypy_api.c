
long pypy_jit_start_addr(void)
{
	return 3;
}

long pypy_jit_end_addr(void)
{
	return 3;
}

long pypy_jit_stack_depth_at_loc(long x)
{
	return 0;
}

long pypy_find_codemap_at_addr(long x)
{
	return 0;
}

long pypy_yield_codemap_at_addr(long x, long y, long *a)
{
	return 0;
}

void pypy_pyframe_execute_frame(void)
{
}

volatile int pypy_codemap_currently_invalid = 0;
