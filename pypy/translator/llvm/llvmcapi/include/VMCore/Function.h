#ifndef __FUNCTION_H__
#define __FUNCTION_H__

#ifdef __cplusplus
extern "C" {
#endif

void        Function_eraseFromParent(void* F);
const void* Function_getFunctionType(void* F);

#ifdef __cplusplus
};
#endif

#endif
