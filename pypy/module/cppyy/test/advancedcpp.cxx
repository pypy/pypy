#include "advancedcpp.h"


// for testing of default arguments
defaulter::defaulter(int a, int b, int c ) {
   m_a = a;
   m_b = b;
   m_c = c;
}


// for esoteric inheritance testing
int get_a( a_class& a ) { return a.m_a; }
int get_b( b_class& b ) { return b.m_b; }
int get_c( c_class& c ) { return c.m_c; }
int get_d( d_class& d ) { return d.m_d; }


// for namespace testing
int a_ns::g_a                         = 11;
int a_ns::b_class::s_b                = 22;
int a_ns::b_class::c_class::s_c       = 33;
int a_ns::d_ns::g_d                   = 44;
int a_ns::d_ns::e_class::s_e          = 55;
int a_ns::d_ns::e_class::f_class::s_f = 66;


// for template testing
template class T1<int>;
template class T2<T1<int> >;
template class T3<int, double>;
template class T3<T1<int>, T2<T1<int> > >;
template class a_ns::T4<int>;
template class a_ns::T4<a_ns::T4<T3<int, double> > >;


// helpers for checking pass-by-ref
void set_int_through_ref(int& i, int val)             { i = val; }
int pass_int_through_const_ref(const int& i)          { return i; }
void set_long_through_ref(long& l, long val)          { l = val; }
long pass_long_through_const_ref(const long& l)       { return l; }
void set_double_through_ref(double& d, double val)    { d = val; }
double pass_double_through_const_ref(const double& d) { return d; }


// for math conversions testing
bool operator==(const some_comparable& c1, const some_comparable& c2 )
{
   return &c1 != &c2;              // the opposite of a pointer comparison
}

bool operator!=( const some_comparable& c1, const some_comparable& c2 )
{
   return &c1 == &c2;              // the opposite of a pointer comparison
}


// a couple of globals for access testing
double my_global_double = 12.;
double my_global_array[500];


// for life-line testing
int some_class_with_data::some_data::s_num_data = 0;


// for testing multiple inheritance
multi1::~multi1() {}
multi2::~multi2() {}
multi::~multi() {}
