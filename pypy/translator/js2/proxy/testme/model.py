from sqlobject import *
from turbogears.database import PackageHub

hub = PackageHub("testme")
__connection__ = hub

# class YourDataClass(SQLObject):
#     pass
