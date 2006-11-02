//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

void    restart();
int     compile(const char* filename);
int     compile_src(const char* src);
int     execute(const char* funcname, int param);

#ifdef  __cplusplus    
}
#endif
