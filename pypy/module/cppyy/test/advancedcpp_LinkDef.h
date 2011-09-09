#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ class defaulter;

#pragma link C++ class base_class;
#pragma link C++ class derived_class;

#pragma link C++ class a_class;
#pragma link C++ class b_class;
#pragma link C++ class c_class;
#pragma link C++ class c_class_1;
#pragma link C++ class c_class_2;
#pragma link C++ class d_class;

#pragma link C++ function get_a(a_class&);
#pragma link C++ function get_b(b_class&);
#pragma link C++ function get_c(c_class&);
#pragma link C++ function get_d(d_class&);

#pragma link C++ class T1<int>;
#pragma link C++ class T2<T1<int> >;
#pragma link C++ class T3<int, double>;
#pragma link C++ class T3<T1<int>, T2<T1<int> > >;
#pragma link C++ class a_ns::T4<int>;
#pragma link C++ class a_ns::T4<T3<int,double> >;
#pragma link C++ class a_ns::T4<a_ns::T4<T3<int, double> > >;

#pragma link C++ namespace a_ns;
#pragma link C++ namespace a_ns::d_ns;
#pragma link C++ struct a_ns::b_class;
#pragma link C++ struct a_ns::b_class::c_class;
#pragma link C++ struct a_ns::d_ns::e_class;
#pragma link C++ struct a_ns::d_ns::e_class::f_class;
#pragma link C++ variable a_ns::g_a;
#pragma link C++ variable a_ns::d_ns::g_d;

#pragma link C++ class some_abstract_class;
#pragma link C++ class some_concrete_class;
#pragma link C++ class some_convertible;
#pragma link C++ class some_class_with_data;
#pragma link C++ class some_class_with_data::some_data;

#pragma link C++ class pointer_pass;

#pragma link C++ class multi1;
#pragma link C++ class multi2;
#pragma link C++ class multi;

#endif
