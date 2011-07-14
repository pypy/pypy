#ifndef CPPYY_CPPYY
#define CPPYY_CPPYY

#define CPPYY_G__MAXFUNCPARA   40

#ifdef __cplusplus
struct CPPYY_G__DUMMY_FOR_CINT7 {
#else
typedef struct
#endif
   void* fTypeName;
   unsigned int fModifiers;
#ifdef __cplusplus
};
#else
} CPPYY_G__DUMMY_FOR_CINT7;
#endif

#ifdef __cplusplus
struct CPPYY_G__p2p {
#else
#typedef struct
#endif
  long i;
  int reftype;
#ifdef __cplusplus
};
#else
} CPPYY_G__p2p;
#endif


#ifdef __cplusplus
struct CPPYY_G__value {
#else
typedef struct {
#endif
  union {
    double d;
    long    i; /* used to be int */
    struct CPPYY_G__p2p reftype;
    char ch;
    short sh;
    int in;
    float fl;
    unsigned char uch;
    unsigned short ush;
    unsigned int uin;
    unsigned long ulo;
    long long ll;
    unsigned long long ull;
    long double ld;
  } obj;
  long ref;
  int type;
  int tagnum;
  int typenum;
  char isconst;
  struct CPPYY_G__DUMMY_FOR_CINT7 dummyForCint7;
#ifdef __cplusplus
};
#else
} CPPYY_G__value;
#endif


#ifdef __cplusplus
struct CPPYY_G__param {
#else
typedef struct
#endif
  int paran;
  long para;  /* place-holder */
  /* dropped parameter as it appears unused in stub functions */
#ifdef __cplusplus
};
#else
} CPPYY_G__param;
#endif

#endif // CPPYY_CPPYY
