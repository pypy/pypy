from sqlobject import *
from turbogears.database import PackageHub

hub = PackageHub("jsdemo")
__connection__ = hub

# class YourDataClass(SQLObject):
#     pass
