//for using the LLVM C++ API

#ifdef  __cplusplus
extern "C" {
#endif

void    restart();
int     transform(const char* passnames);
int     parse(const char* llsource);
void*   find_function(const char* funcname);
int     freeMachineCodeForFunction(const void* function);
int     recompile(const void* function);
int     execute(const void* function, int param);
int     get_global_data();
void    set_global_data(int n);
int*    get_pointer_to_global_data();
void    add_global_mapping(const char* name, void* address); 

#ifdef  __cplusplus    
}
#endif
