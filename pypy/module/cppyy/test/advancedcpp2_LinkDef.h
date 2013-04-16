#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ namespace a_ns;
#pragma link C++ namespace a_ns::d_ns;
#pragma link C++ struct a_ns::g_class;
#pragma link C++ struct a_ns::g_class::h_class;
#pragma link C++ struct a_ns::d_ns::i_class;
#pragma link C++ struct a_ns::d_ns::i_class::j_class;
#pragma link C++ variable a_ns::g_g;
#pragma link C++ function a_ns::get_g_g;
#pragma link C++ variable a_ns::d_ns::g_i;
#pragma link C++ function a_ns::d_ns::get_g_i;

#endif
