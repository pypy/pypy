#include <list>
#include <map>
#include <string>
#include <vector>

#define STLTYPES_EXPLICIT_INSTANTIATION(STLTYPE, TTYPE)                         \
template class std::STLTYPE< TTYPE >;                                           \
template class __gnu_cxx::__normal_iterator<TTYPE*, std::STLTYPE< TTYPE > >;    \
template class __gnu_cxx::__normal_iterator<const TTYPE*, std::STLTYPE< TTYPE > >;


//- basic example class
class just_a_class {
public:
    int m_i;
};


//- explicit instantiations of used types
STLTYPES_EXPLICIT_INSTANTIATION(vector, int)
STLTYPES_EXPLICIT_INSTANTIATION(vector, just_a_class)
