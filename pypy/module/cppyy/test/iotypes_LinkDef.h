#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

using namespace std;
#pragma link C++ class vector<vector<float> >+;
#pragma link C++ class vector<vector<float> >::iterator;
#pragma link C++ class vector<vector<float> >::const_iterator;

#pragma link C++ namespace IO;
#pragma link C++ class IO::SomeDataObject+;
#pragma link C++ class IO::SomeDataStruct+;

#endif
