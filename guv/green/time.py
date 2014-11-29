__time = __import__('time')
from ..patcher import slurp_properties

__patched__ = ['sleep']
slurp_properties(__time, globals(), ignore=__patched__, srckeys=dir(__time))
from ..greenthread import sleep

sleep  # silence pyflakes
