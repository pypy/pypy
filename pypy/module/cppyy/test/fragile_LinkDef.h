#ifdef __CINT__

#pragma link off all globals;
#pragma link off all classes;
#pragma link off all functions;

#pragma link C++ namespace fragile;
#pragma link C++ namespace fragile::nested1;
#pragma link C++ namespace fragile::nested1::nested2;
#pragma link C++ namespace fragile::nested1::nested2::nested3;

#pragma link C++ class fragile::A;
#pragma link C++ class fragile::B;
#pragma link C++ class fragile::C;
#pragma link C++ class fragile::D;
#pragma link C++ class fragile::E;
#pragma link C++ class fragile::F;
#pragma link C++ class fragile::G;
#pragma link C++ class fragile::H;
#pragma link C++ class fragile::I;
#pragma link C++ class fragile::J;
#pragma link C++ class fragile::K;
#pragma link C++ class fragile::L;
#pragma link C++ class fragile::M;
#pragma link C++ class fragile::N;
#pragma link C++ class fragile::O;
#pragma link C++ class fragile::nested1::A;
#pragma link C++ class fragile::nested1::nested2::A;
#pragma link C++ class fragile::nested1::nested2::nested3::A;

#pragma link C++ variable fragile::gI;

#pragma link C++ function fragile::fglobal;

#endif
