
long pypy_jit_start_addr();
long pypy_jit_end_addr();
long pypy_jit_stack_depth_at_loc(long);
void *pypy_find_codemap_at_addr(long);
long pypy_yield_codemap_at_addr(void *, long, long *);

extern volatile int pypy_codemap_currently_invalid;

void vmprof_set_tramp_range(void* start, void* end)
{
}

int custom_sanity_check()
{
	return !pypy_codemap_currently_invalid;
}

static ptrdiff_t vmprof_unw_get_custom_offset(void* ip, unw_cursor_t *cp) {
	intptr_t ip_l = (intptr_t)ip;

	if (ip_l < pypy_jit_start_addr() || ip_l > pypy_jit_end_addr()) {
		return -1;
	}
	return (void*)pypy_jit_stack_depth_at_loc(ip_l);
}

static long vmprof_write_header_for_jit_addr(void **result, long n,
											 void *ip, int max_depth)
{
	void *codemap;
	long current_pos = 0;
	intptr_t id;
	intptr_t addr = (intptr_t)ip;

	codemap = pypy_find_codemap_at_addr(addr);
	if (codemap == NULL)
		return n;

	while (n < max_depth) {
		id = pypy_yield_codemap_at_addr(codemap, addr, &current_pos);
		if (id == 0)
			break;
		result[n++] = (void *)id;
	}
	return n;
}
