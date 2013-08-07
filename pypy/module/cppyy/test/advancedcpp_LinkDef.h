#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ class short_defaulter;
#pragma link C++ class ushort_defaulter;
#pragma link C++ class int_defaulter;
#pragma link C++ class uint_defaulter;
#pragma link C++ class long_defaulter;
#pragma link C++ class ulong_defaulter;
#pragma link C++ class llong_defaulter;
#pragma link C++ class ullong_defaulter;
#pragma link C++ class float_defaulter;
#pragma link C++ class double_defaulter;

#pragma link C++ class base_class;
#pragma link C++ class derived_class;

#pragma link C++ class a_class;
#pragma link C++ class b_class;
#pragma link C++ class c_class;
#pragma link C++ class c_class_1;
#pragma link C++ class c_class_2;
#pragma link C++ class d_class;

#pragma link C++ function create_c1();
#pragma link C++ function create_c2();

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
#pragma link C++ function a_ns::get_g_a;
#pragma link C++ variable a_ns::d_ns::g_d;
#pragma link C++ function a_ns::d_ns::get_g_d;

#pragma link C++ class some_abstract_class;
#pragma link C++ class some_concrete_class;
#pragma link C++ class some_convertible;
#pragma link C++ class some_class_with_data;
#pragma link C++ class some_class_with_data::some_data;

#pragma link C++ class some_comparable;
#pragma link C++ function operator==(const some_comparable&, const some_comparable&);
#pragma link C++ function operator!=(const some_comparable&, const some_comparable&);

#pragma link C++ class ref_tester;
#pragma link C++ class std::vector<ref_tester>;
#pragma link C++ class pointer_pass;

#pragma link C++ class multi1;
#pragma link C++ class multi2;
#pragma link C++ class multi;

#pragma link C++ class new_overloader;

#pragma link C++ class my_templated_class<std::vector<float> >;
#pragma link C++ function my_templated_function<char>(char);
#pragma link C++ function my_templated_function<double>(double);
#pragma link C++ class my_templated_method_class;
#pragma link C++ typedef my_typedef_t;

#pragma link C++ class overload_one_way;
#pragma link C++ class overload_the_other_way;

#endif
