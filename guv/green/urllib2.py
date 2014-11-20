from guv import patcher
from guv.green import ftplib
from guv.green import httplib
from guv.green import socket
from guv.green import time
from guv.green import urllib

patcher.inject(
    'urllib2',
    globals(),
    ('httplib', httplib),
    ('socket', socket),
    ('time', time),
    ('urllib', urllib))

FTPHandler.ftp_open = patcher.patch_function(FTPHandler.ftp_open, ('ftplib', ftplib))

del patcher
