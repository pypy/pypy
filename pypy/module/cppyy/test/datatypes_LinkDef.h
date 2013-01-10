#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ struct cppyy_test_pod;
#pragma link C++ class cppyy_test_data;

#pragma link C++ function get_pod_address(cppyy_test_data&);
#pragma link C++ function get_int_address(cppyy_test_data&);
#pragma link C++ function get_double_address(cppyy_test_data&);
#pragma link C++ function set_global_int(int);
#pragma link C++ function get_global_int();

#pragma link C++ function is_global_pod(cppyy_test_pod*);
#pragma link C++ function set_global_pod(cppyy_test_pod*);
#pragma link C++ function get_global_pod();

#pragma link C++ global N;
#pragma link C++ global g_int;
#pragma link C++ global g_pod;

#endif
