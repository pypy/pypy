//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

void    restart();
int     transform(const char* passnames);
int     compile(const char* llsource);
void*   find_function(const char* funcname);
int     execute(const void* function, int param);
char*   get_pointer_to_global_char();
void    add_global_mapping(const char* name, void* address); 

#ifdef  __cplusplus    
}
#endif
