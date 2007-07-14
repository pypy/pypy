
gbls = globals()

import ll_SDL

for name, value in ll_SDL.__dict__.iteritems():
    if name.startswith('SDL_'):
        gbls[name[len('SDL_'):]] = value
    if name.startswith('SDLK_'):
        gbls[name[len('SDL'):]] = value
    if name.startswith('KMOD_'):
        gbls[name] = value

BlitSurface = UpperBlit


