import objectspace

#######################
####  __builtin__  ####
#######################


class methodtable:

    def chr(space, w_ascii):
        w_character = space.newstring([w_ascii])
        return w_character

