#include "advancedcpp.h"


// for testing of default arguments
#define IMPLEMENT_DEFAULTER_CLASS(type, tname)                               \
tname##_defaulter::tname##_defaulter(type a, type b, type c) {               \
   m_a = a; m_b = b; m_c = c;                                                \
}
IMPLEMENT_DEFAULTER_CLASS(short, short)
IMPLEMENT_DEFAULTER_CLASS(unsigned short, ushort)
IMPLEMENT_DEFAULTER_CLASS(int, int)
IMPLEMENT_DEFAULTER_CLASS(unsigned, uint)
IMPLEMENT_DEFAULTER_CLASS(long, long)
IMPLEMENT_DEFAULTER_CLASS(unsigned long, ulong)
IMPLEMENT_DEFAULTER_CLASS(long long, llong)
IMPLEMENT_DEFAULTER_CLASS(unsigned long long, ullong)
IMPLEMENT_DEFAULTER_CLASS(float, float)
IMPLEMENT_DEFAULTER_CLASS(double, double)


// for esoteric inheritance testing
a_class* create_c1() { return new c_class_1; }
a_class* create_c2() { return new c_class_2; }

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

int a_ns::get_g_a() { return g_a; }
int a_ns::d_ns::get_g_d() { return g_d; }


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
static double sd = 1234.;
double* my_global_ptr = &sd;

// for life-line and identity testing
int some_class_with_data::some_data::s_num_data = 0;


// for testing multiple inheritance
multi1::~multi1() {}
multi2::~multi2() {}
multi::~multi() {}


// for testing calls to overloaded new
int new_overloader::s_instances = 0;

void* new_overloader::operator new(std::size_t size) {
    ++s_instances;
    return ::operator new(size);
}

void* new_overloader::operator new(std::size_t, void* p) throw() {
    // no ++s_instances, as no memory is allocated
    return p;
}

void new_overloader::operator delete(void* p, std::size_t) {
    if (p == 0) return;
    --s_instances;
    ::operator delete(p);
}


// more template testing
long my_templated_method_class::get_size() { return -1; }

long my_templated_method_class::get_char_size()   { return (long)sizeof(char); }
long my_templated_method_class::get_int_size()    { return (long)sizeof(int); }
long my_templated_method_class::get_long_size()   { return (long)sizeof(long); }
long my_templated_method_class::get_float_size()  { return (long)sizeof(float); }
long my_templated_method_class::get_double_size() { return (long)sizeof(double); }
long my_templated_method_class::get_self_size()   { return (long)sizeof(my_templated_method_class); }


// overload order testing
int overload_one_way::gime() const { return 1; }
std::string overload_one_way::gime() { return "aap"; }

std::string overload_the_other_way::gime() { return "aap"; }
int overload_the_other_way::gime() const { return 1; }
