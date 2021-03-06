#!/usr/bin/env python
# vim: set encoding=utf-8 tabstop=4 softtabstop=4 shiftwidth=4 expandtab
#########################################################################
# Copyright 2012-2013 Marcus Popp                          marcus@popp.mx
#########################################################################
#  This file is part of SmartHome.py.   http://smarthome.sourceforge.net/
#
#  SmartHome.py is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SmartHome.py is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SmartHome.py.  If not, see <http://www.gnu.org/licenses/>.
#########################################################################

import logging
import math
import datetime
import urllib2
import subprocess
import base64

logger = logging.getLogger('')


class Tools():

    def __init__(self):
        self._start = datetime.datetime.now()

    def ping(self, host):
        try:
            retcode = subprocess.call("ping -W 1 -c 1 " + host + " > /dev/null", shell=True)
            if retcode == 0:
                return True
            else:
                return False
        except OSError:
            return False

    def dewpoint(self, t, rf):
        log = math.log((rf + 0.01) / 100)  # + 0.01 to 'cast' float
        return round((241.2 * log + 4222.03716 * t / (241.2 + t)) / (17.5043 - log - 17.5043 * t / (241.2 + t)), 2)

    def runtime(self):
        return datetime.datetime.now() - self._start

    def fetch_url(self, uri, username=None, password=None, timeout=2):
        try:
            r = urllib2.Request(uri)
            if username and password:
                r.add_header('Authorization', 'Basic ' + base64.b64encode(username + ':' + password))
            u = urllib2.urlopen(r, timeout=timeout)
            data = u.read()
            u.fp._sock.recv = None
            u.close()
            del(r, u)
            return data
        except Exception, e:
            logger.warning("Problem fetching {0}: {1}".format(uri, e))
            return False
