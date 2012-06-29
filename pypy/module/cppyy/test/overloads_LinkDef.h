#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ class a_overload;
#pragma link C++ class b_overload;
#pragma link C++ class c_overload;
#pragma link C++ class d_overload;

#pragma link C++ namespace ns_a_overload;
#pragma link C++ class ns_a_overload::a_overload;
#pragma link C++ class ns_a_overload::b_overload;

#pragma link C++ class ns_b_overload;
#pragma link C++ class ns_b_overload::a_overload;

#pragma link C++ class aa_ol;
#pragma link C++ class cc_ol;

#pragma link C++ class more_overloads;
#pragma link C++ class more_overloads2;

#endif
