
long pypy_jit_start_addr();
long pypy_jit_end_addr();
long pypy_jit_stack_depth_at_loc(long);

static ptrdiff_t vmprof_unw_get_custom_offset(void* ip) {
	long ip_l = (long)ip;

	if (ip < pypy_jit_start_addr() || ip > pypy_jit_end_addr()) {
		return -1;
	}
	return pypy_jit_stack_depth_at_loc(ip);
}
