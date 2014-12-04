import sys
from ..patcher import copy_attributes

if sys.version_info >= (3, 3):
    from . import _ssl33 as _ssl3
else:
    # Python 3.2
    from . import _ssl32 as _ssl3

copy_attributes(_ssl3, globals(), srckeys=dir(_ssl3))
__patched__ = _ssl3.__patched__
