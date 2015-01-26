
long pypy_jit_start_addr();
long pypy_jit_end_addr();
long pypy_jit_stack_depth_at_loc(long);
long pypy_find_codemap_at_addr(long);
long pypy_yield_bytecode_at_addr(long, long, long*);

static ptrdiff_t vmprof_unw_get_custom_offset(void* ip) {
	intptr_t ip_l = (intptr_t)ip;

	if (ip_l < pypy_jit_start_addr() || ip_l > pypy_jit_end_addr()) {
		return -1;
	}
	return (void*)pypy_jit_stack_depth_at_loc(ip_l);
}

static long vmprof_write_header_for_jit_addr(void **result, long n,
											 void *ip, int max_depth)
{
	long codemap_pos;
	long current_pos = 0;
	intptr_t id;
	intptr_t addr = (intptr_t)ip;

	if (addr < pypy_jit_start_addr() || addr > pypy_jit_end_addr()) {
		return n;
	}
	codemap_pos = pypy_find_codemap_at_addr(addr);
	if (codemap_pos == -1) {
		return n;
	}
	while (1) {
		id = pypy_yield_bytecode_at_addr(codemap_pos, addr, &current_pos);
		if (id == 0) {
			return n;
		}
		result[n++] = id;
		if (n >= max_depth) {
			return n;
		}
	}
}
