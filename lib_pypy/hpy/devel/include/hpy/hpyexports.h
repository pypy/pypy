#ifndef HPy_EXPORTS_H
#define HPy_EXPORTS_H

// Copied from Python's exports.h
#ifndef HPy_EXPORTED_SYMBOL
    #if defined(_WIN32) || defined(__CYGWIN__)
        #define HPy_EXPORTED_SYMBOL __declspec(dllexport)
    #else
        #define HPy_EXPORTED_SYMBOL __attribute__ ((visibility ("default")))
    #endif
#endif

#endif /* HPy_EXPORTS_H */
