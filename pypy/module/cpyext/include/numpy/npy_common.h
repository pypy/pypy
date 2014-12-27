#ifndef _NPY_COMMON_H_
#define _NPY_COMMON_H_

typedef Py_intptr_t npy_intp;
typedef Py_uintptr_t npy_uintp;
typedef unsigned char npy_bool;
typedef long npy_int32;
typedef unsigned long npy_uint32;
typedef unsigned long npy_ucs4;
typedef long npy_int64;
typedef unsigned long npy_uint64;
typedef unsigned char npy_uint8;
#if defined(_MSC_VER)
        #define NPY_INLINE __inline
#elif defined(__GNUC__)
	#if defined(__STRICT_ANSI__)
		#define NPY_INLINE __inline__
	#else
		#define NPY_INLINE inline
	#endif
#else
        #define NPY_INLINE
#endif
#ifndef NPY_INTP_FMT
#define NPY_INTP_FMT "ld"
#endif
#define NPY_API_VERSION 0x8
#endif //_NPY_COMMON_H_

