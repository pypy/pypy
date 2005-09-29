
def run_translator_server(t, options):
    from pypy.translator.tool import graphpage
    import pygame
    from pypy.translator.tool.pygame.graphclient import get_layout
    from pypy.translator.tool.pygame.graphdisplay import GraphDisplay

    if len(t.functions) <= options.huge:
        page = graphpage.TranslatorPage(t)
    else:
        page = graphpage.LocalizedCallGraphPage(t, entry_point)

    layout = get_layout(page)
    show, async_quit = layout.connexion.initiate_display, layout.connexion.quit
    display = layout.get_display()
    return display.run, show, async_quit, pygame.quit

