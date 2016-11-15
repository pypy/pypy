#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ class example01;
#pragma link C++ typedef example01_t;
#pragma link C++ class example01a;
#pragma link C++ class payload;
#pragma link C++ class ArgPasser;
#pragma link C++ class z_;

#pragma link C++ function globalAddOneToInt(int);
#pragma link C++ function installableAddOneToInt(example01&, int);

#pragma link C++ namespace ns_example01;
#pragma link C++ function ns_example01::globalAddOneToInt(int);

#pragma link C++ variable ns_example01::gMyGlobalInt;

#endif
