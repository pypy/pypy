#include "fragile.h"

fragile::H::HH* fragile::H::HH::copy() {
    return (HH*)0;
}

fragile::I fragile::gI;

void fragile::fglobal(int, double, char) {
    /* empty; only used for doc-string testing */
}
