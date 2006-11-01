//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

int testme(int n);
void* compile(const char* filename);
int execute(void* compiled, const char* funcname, int param);

#ifdef  __cplusplus    
}
#endif
