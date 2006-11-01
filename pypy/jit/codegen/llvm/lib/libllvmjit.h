//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

int compile(const char* filename);
int execute(const char* funcname, int param);

#ifdef  __cplusplus    
}
#endif
