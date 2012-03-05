#include "datatypes.h"


//===========================================================================
cppyy_test_data::cppyy_test_data() : m_owns_arrays(false)
{
    m_bool   = false;
    m_char   = 'a';
    m_uchar  = 'c';
    m_short  = -11;
    m_ushort =  11u;
    m_int    = -22;
    m_uint   =  22u;
    m_long   = -33l;
    m_ulong  =  33ul;
    m_float  = -44.f;
    m_double = -55.;
    m_enum   = kNothing;

    m_short_array2  = new short[N];
    m_ushort_array2 = new unsigned short[N];
    m_int_array2    = new int[N];
    m_uint_array2   = new unsigned int[N];
    m_long_array2   = new long[N];
    m_ulong_array2  = new unsigned long[N];

    m_float_array2  = new float[N];
    m_double_array2 = new double[N];

    for (int i = 0; i < N; ++i) {
        m_short_array[i]   =  -1*i;
        m_short_array2[i]  =  -2*i;
        m_ushort_array[i]  =   3u*i;
        m_ushort_array2[i] =   4u*i;
        m_int_array[i]     =  -5*i;
        m_int_array2[i]    =  -6*i;
        m_uint_array[i]    =   7u*i;
        m_uint_array2[i]   =   8u*i;
        m_long_array[i]    =  -9l*i;
        m_long_array2[i]   = -10l*i;
        m_ulong_array[i]   =  11ul*i;
        m_ulong_array2[i]  =  12ul*i;

        m_float_array[i]   = -13.f*i;
        m_float_array2[i]  = -14.f*i;
        m_double_array[i]  = -15.*i;
        m_double_array2[i] = -16.*i;
    }

    m_owns_arrays = true;

    m_pod.m_int    = 888;
    m_pod.m_double = 3.14;
};

cppyy_test_data::~cppyy_test_data()
{
    destroy_arrays();
}

void cppyy_test_data::destroy_arrays() {
    if (m_owns_arrays == true) {
        delete[] m_short_array2;
        delete[] m_ushort_array2;
        delete[] m_int_array2;
        delete[] m_uint_array2;
        delete[] m_long_array2;
        delete[] m_ulong_array2;

        delete[] m_float_array2;
        delete[] m_double_array2;

        m_owns_arrays = false;
    }
}

//- getters -----------------------------------------------------------------
bool           cppyy_test_data::get_bool()   { return m_bool; }
char           cppyy_test_data::get_char()   { return m_char; }
unsigned char  cppyy_test_data::get_uchar()  { return m_uchar; }
short          cppyy_test_data::get_short()  { return m_short; }
unsigned short cppyy_test_data::get_ushort() { return m_ushort; }
int            cppyy_test_data::get_int()    { return m_int; }
unsigned int   cppyy_test_data::get_uint()   { return m_uint; }
long           cppyy_test_data::get_long()   { return m_long; }
unsigned long  cppyy_test_data::get_ulong()  { return m_ulong; }
float          cppyy_test_data::get_float()  { return m_float; }
double         cppyy_test_data::get_double() { return m_double; }
cppyy_test_data::what cppyy_test_data::get_enum() { return m_enum; }

short*          cppyy_test_data::get_short_array()   { return m_short_array; }
short*          cppyy_test_data::get_short_array2()  { return m_short_array2; }
unsigned short* cppyy_test_data::get_ushort_array()  { return m_ushort_array; }
unsigned short* cppyy_test_data::get_ushort_array2() { return m_ushort_array2; }
int*            cppyy_test_data::get_int_array()     { return m_int_array; }
int*            cppyy_test_data::get_int_array2()    { return m_int_array2; }
unsigned int*   cppyy_test_data::get_uint_array()    { return m_uint_array; }
unsigned int*   cppyy_test_data::get_uint_array2()   { return m_uint_array2; }
long*           cppyy_test_data::get_long_array()    { return m_long_array; }
long*           cppyy_test_data::get_long_array2()   { return m_long_array2; }
unsigned long*  cppyy_test_data::get_ulong_array()   { return m_ulong_array; }
unsigned long*  cppyy_test_data::get_ulong_array2()  { return m_ulong_array2; }

float*  cppyy_test_data::get_float_array()   { return m_float_array; }
float*  cppyy_test_data::get_float_array2()  { return m_float_array2; }
double* cppyy_test_data::get_double_array()  { return m_double_array; }
double* cppyy_test_data::get_double_array2() { return m_double_array2; }

//- setters -----------------------------------------------------------------
void cppyy_test_data::set_bool(bool b)              { m_bool   = b; }
void cppyy_test_data::set_char(char c)              { m_char   = c; }
void cppyy_test_data::set_uchar(unsigned char uc)   { m_uchar  = uc; }
void cppyy_test_data::set_short(short s)            { m_short  = s; }
void cppyy_test_data::set_ushort(unsigned short us) { m_ushort = us; }
void cppyy_test_data::set_int(int i)                { m_int    = i; }
void cppyy_test_data::set_uint(unsigned int ui)     { m_uint   = ui; }
void cppyy_test_data::set_long(long l)              { m_long   = l; }
void cppyy_test_data::set_ulong(unsigned long ul)   { m_ulong  = ul; }
void cppyy_test_data::set_float(float f)            { m_float  = f; }
void cppyy_test_data::set_double(double d)          { m_double = d; }
void cppyy_test_data::set_enum(what w)              { m_enum   = w; }

char           cppyy_test_data::s_char   = 's';
unsigned char  cppyy_test_data::s_uchar  = 'u';
short          cppyy_test_data::s_short  = -101;
unsigned short cppyy_test_data::s_ushort =  255u;
int            cppyy_test_data::s_int    = -202;
unsigned int   cppyy_test_data::s_uint   =  202u;
long           cppyy_test_data::s_long   = -303l;
unsigned long  cppyy_test_data::s_ulong  =  303ul;
float          cppyy_test_data::s_float  = -404.f;
double         cppyy_test_data::s_double = -505.;
cppyy_test_data::what  cppyy_test_data::s_enum = cppyy_test_data::kNothing;


//= global functions ========================================================
long get_pod_address(cppyy_test_data& c)
{
    return (long)&c.m_pod;
}

long get_int_address(cppyy_test_data& c)
{
    return (long)&c.m_pod.m_int;
}

long get_double_address(cppyy_test_data& c)
{
    return (long)&c.m_pod.m_double;
}

//= global variables/pointers ===============================================
int g_int = 42;

void set_global_int(int i) {
   g_int = i;
}

int get_global_int() {
   return g_int;
}

cppyy_test_pod* g_pod = (cppyy_test_pod*)0;

bool is_global_pod(cppyy_test_pod* t) {
   return t == g_pod;
}

void set_global_pod(cppyy_test_pod* t) {
   g_pod = t;
}

cppyy_test_pod* get_global_pod() {
   return g_pod;
}
