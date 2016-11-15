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
    m_llong  = -44ll;
    m_ullong =  55ull;
    m_float  = -66.f;
    m_double = -77.;
    m_enum   = kNothing;
    m_voidp  = (void*)0;

    m_bool_array2   = new bool[N];
    m_short_array2  = new short[N];
    m_ushort_array2 = new unsigned short[N];
    m_int_array2    = new int[N];
    m_uint_array2   = new unsigned int[N];
    m_long_array2   = new long[N];
    m_ulong_array2  = new unsigned long[N];

    m_float_array2  = new float[N];
    m_double_array2 = new double[N];

    for (int i = 0; i < N; ++i) {
        m_bool_array[i]    =  bool(i%2);
        m_bool_array2[i]   =  bool((i+1)%2);
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

    m_ppod = &m_pod;
};

cppyy_test_data::~cppyy_test_data()
{
    destroy_arrays();
}

void cppyy_test_data::destroy_arrays() {
    if (m_owns_arrays == true) {
        delete[] m_bool_array2;
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
long long      cppyy_test_data::get_llong()  { return m_llong; }
unsigned long long cppyy_test_data::get_ullong()  { return m_ullong; }
float          cppyy_test_data::get_float()  { return m_float; }
double         cppyy_test_data::get_double() { return m_double; }
cppyy_test_data::what cppyy_test_data::get_enum() { return m_enum; }
void*          cppyy_test_data::get_voidp()  { return m_voidp; }

bool*           cppyy_test_data::get_bool_array()    { return m_bool_array; }
bool*           cppyy_test_data::get_bool_array2()   { return m_bool_array2; }
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

cppyy_test_pod cppyy_test_data::get_pod_val() { return m_pod; }
cppyy_test_pod* cppyy_test_data::get_pod_val_ptr() { return &m_pod; }
cppyy_test_pod& cppyy_test_data::get_pod_val_ref() { return m_pod; }
cppyy_test_pod*& cppyy_test_data::get_pod_ptrref() { return m_ppod; }

cppyy_test_pod* cppyy_test_data::get_pod_ptr() { return m_ppod; }

//- setters -----------------------------------------------------------------
void cppyy_test_data::set_bool(bool b)                       { m_bool   = b; }
void cppyy_test_data::set_char(char c)                       { m_char   = c; }
void cppyy_test_data::set_uchar(unsigned char uc)            { m_uchar  = uc; }
void cppyy_test_data::set_short(short s)                     { m_short  = s; }
void cppyy_test_data::set_short_c(const short& s)            { m_short  = s; }
void cppyy_test_data::set_ushort(unsigned short us)          { m_ushort = us; }
void cppyy_test_data::set_ushort_c(const unsigned short& us) { m_ushort = us; }
void cppyy_test_data::set_int(int i)                         { m_int    = i; }
void cppyy_test_data::set_int_c(const int& i)                { m_int    = i; }
void cppyy_test_data::set_uint(unsigned int ui)              { m_uint   = ui; }
void cppyy_test_data::set_uint_c(const unsigned int& ui)     { m_uint   = ui; }
void cppyy_test_data::set_long(long l)                       { m_long   = l; }
void cppyy_test_data::set_long_c(const long& l)              { m_long   = l; }
void cppyy_test_data::set_ulong(unsigned long ul)            { m_ulong  = ul; }
void cppyy_test_data::set_ulong_c(const unsigned long& ul)   { m_ulong  = ul; }
void cppyy_test_data::set_llong(long long ll)                { m_llong  = ll; }
void cppyy_test_data::set_llong_c(const long long& ll)       { m_llong  = ll; }
void cppyy_test_data::set_ullong(unsigned long long ull)     { m_ullong  = ull; }
void cppyy_test_data::set_ullong_c(const unsigned long long& ull) { m_ullong  = ull; }
void cppyy_test_data::set_float(float f)                     { m_float  = f; }
void cppyy_test_data::set_float_c(const float& f)            { m_float  = f; }
void cppyy_test_data::set_double(double d)                   { m_double = d; }
void cppyy_test_data::set_double_c(const double& d)          { m_double = d; }
void cppyy_test_data::set_enum(what w)                       { m_enum   = w; }
void cppyy_test_data::set_voidp(void* p)                     { m_voidp  = p; }

void cppyy_test_data::set_pod_val(cppyy_test_pod p)            { m_pod = p; }
void cppyy_test_data::set_pod_ptr_in(cppyy_test_pod* pp)       { m_pod = *pp; }
void cppyy_test_data::set_pod_ptr_out(cppyy_test_pod* pp)      { *pp = m_pod; }
void cppyy_test_data::set_pod_ref(const cppyy_test_pod& rp)    { m_pod = rp; }
void cppyy_test_data::set_pod_ptrptr_in(cppyy_test_pod** ppp)  { m_pod = **ppp; }
void cppyy_test_data::set_pod_void_ptrptr_in(void** pp)        { m_pod = **((cppyy_test_pod**)pp); }
void cppyy_test_data::set_pod_ptrptr_out(cppyy_test_pod** ppp) { delete *ppp; *ppp = new cppyy_test_pod(m_pod); }
void cppyy_test_data::set_pod_void_ptrptr_out(void** pp)       { delete *((cppyy_test_pod**)pp);
                                                                 *((cppyy_test_pod**)pp) = new cppyy_test_pod(m_pod); }

void cppyy_test_data::set_pod_ptr(cppyy_test_pod* pp)          { m_ppod = pp; }

//- passers -----------------------------------------------------------------
short*          cppyy_test_data::pass_array(short* a)          { return a; }
unsigned short* cppyy_test_data::pass_array(unsigned short* a) { return a; }
int*            cppyy_test_data::pass_array(int* a)            { return a; }
unsigned int*   cppyy_test_data::pass_array(unsigned int* a)   { return a; }
long*           cppyy_test_data::pass_array(long* a)           { return a; }
unsigned long*  cppyy_test_data::pass_array(unsigned long* a)  { return a; }
float*          cppyy_test_data::pass_array(float* a)          { return a; }
double*         cppyy_test_data::pass_array(double* a)         { return a; }

char                cppyy_test_data::s_char   = 's';
unsigned char       cppyy_test_data::s_uchar  = 'u';
short               cppyy_test_data::s_short  = -101;
unsigned short      cppyy_test_data::s_ushort =  255u;
int                 cppyy_test_data::s_int    = -202;
unsigned int        cppyy_test_data::s_uint   =  202u;
long                cppyy_test_data::s_long   = -303l;
unsigned long       cppyy_test_data::s_ulong  =  303ul;
long long           cppyy_test_data::s_llong  = -404ll;
unsigned long long  cppyy_test_data::s_ullong =  505ull;
float               cppyy_test_data::s_float  = -606.f;
double              cppyy_test_data::s_double = -707.;
cppyy_test_data::what  cppyy_test_data::s_enum = cppyy_test_data::kNothing;
void*               cppyy_test_data::s_voidp  = (void*)0;

//- strings -----------------------------------------------------------------
const char* cppyy_test_data::get_valid_string(const char* in) { return in; }
const char* cppyy_test_data::get_invalid_string() { return (const char*)0; }


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

cppyy_test_pod* get_null_pod() {
   return (cppyy_test_pod*)0;
}
