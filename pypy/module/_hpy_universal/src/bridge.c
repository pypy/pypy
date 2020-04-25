#include "bridge.h"

_HPyBridge *hpy_get_bridge(void) {
    static _HPyBridge bridge;
    return &bridge;
}
