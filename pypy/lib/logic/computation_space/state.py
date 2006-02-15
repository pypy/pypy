        
class Succeeded:
    """It contains no choice points but a solution to
       the logic program.
    """
    pass

class Distributable:
    pass

class Distributing:
    pass

class Failed(Exception):
    pass

class Merged:
    """Its constraint store has been added to a parent.
       Any further operation operation on the space is
       an error.
    """
    pass
