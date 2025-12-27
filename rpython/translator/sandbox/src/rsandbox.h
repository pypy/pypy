
void rpy_sandbox_arg_i(unsigned long long i);
void rpy_sandbox_arg_f(double f);
void rpy_sandbox_arg_p(void *p);

void rpy_sandbox_res_v(const char *name_and_sig);
unsigned long long rpy_sandbox_res_i(const char *name_and_sig);
double rpy_sandbox_res_f(const char *name_and_sig);
void *rpy_sandbox_res_p(const char *name_and_sig);
