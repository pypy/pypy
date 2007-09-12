
// we hand craft these in module/support.ll
char *RPyString_AsString(RPyString*);
long RPyString_Size(RPyString*);
RPyString *RPyString_FromString(char *);
int _RPyExceptionOccurred(void);
char* LLVM_RPython_StartupCode(void);

#define RPyRaiseSimpleException(exctype, errormsg) raise##exctype(errormsg)

void RPYTHON_RAISE_OSERROR(int error);
#ifdef RPyListOfString
  RPyListOfString *_RPyListOfString_New(long);
  void _RPyListOfString_SetItem(RPyListOfString *, int, RPyString *);
  RPyString *_RPyListOfString_GetItem(RPyListOfString *, int);
  int _RPyListOfString_Length(RPyListOfString *);
#endif

// XXX end of proto hacks
