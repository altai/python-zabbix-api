# This is a port of the ruby zabbix api found here:
# http://trac.red-tux.net/browser/ruby/api/zbx_api.rb
#
#LGPL 2.1   http://www.gnu.org/licenses/old-licenses/lgpl-2.1.html
#Zabbix API Python Library.
#Original Ruby Library is Copyright (C) 2009 Andrew Nelson nelsonab(at)red-tux(dot)net
#Python Library is Copyright (C) 2009 Brett Lentz brett.lentz(at)gmail(dot)com
#
#This library is free software; you can redistribute it and/or
#modify it under the terms of the GNU Lesser General Public
#License as published by the Free Software Foundation; either
#version 2.1 of the License, or (at your option) any later version.
#
#This library is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#Lesser General Public License for more details.
#
#You should have received a copy of the GNU Lesser General Public
#License along with this library; if not, write to the Free Software
#Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301  USA


# NOTES:
# The API requires zabbix 1.8 or later.
# Currently, not all of the API is implemented, and some functionality is
# broken. This is a work in progress.

import base64
import hashlib
import logging
import string
import sys
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2  # python3
import re
from collections import deque


LOG = logging.getLogger(__name__)

try:
    # Separate module or Python <2.6
    import simplejson as json
except ImportError:
    # Python >=2.6
    import json


def checkauth(fn):
    """ Decorator to check authentication of the decorated method """
    def ret(self, *args):
        self.__checkauth__()
        return fn(self, args)
    return ret


def dojson(name):
    def decorator(fn):
        def wrapper(self, opts):
            LOG.debug(
                "Going to do_request for %s with opts %s"
                % (repr(fn), repr(opts)))
            return self.do_request(self.json_obj(name, opts))['result']
        return wrapper
    return decorator


def dojson2(fn):
    def wrapper(self, method, opts):
        LOG.debug(
            "Going to do_request for %s with opts %s"
            % (repr(fn), repr(opts)))
        return self.do_request(self.json_obj(method, opts))['result']
    return wrapper


class ZabbixAPIException(Exception):
    """ generic zabbix api exception
    code list:
         -32602 - Invalid params (eg already exists)
         -32500 - no permissions
    """
    pass


class AlreadyExists(ZabbixAPIException):
    pass


class InvalidProtoError(ZabbixAPIException):
    """ Recived an invalid proto """
    pass


class ZabbixAPI(object):
    __username__ = ''
    __password__ = ''

    auth = ''
    url = '/api_jsonrpc.php'
    params = None
    method = None
    # HTTP or HTTPS
    proto = 'http'
    # HTTP authentication
    httpuser = None
    httppasswd = None
    timeout = 10
    # sub-class instances.
    user = None
    usergroup = None
    host = None
    item = None
    hostgroup = None
    application = None
    trigger = None
    sysmap = None
    template = None
    drule = None
    # Constructor Params:
    # server: Server to connect to
    # path: Path leading to the zabbix install
    # proto: Protocol to use. http or https
    # We're going to use proto://server/path to find the JSON-RPC api.
    #
    # user: HTTP auth username
    # passwd: HTTP auth password
    # log_level: logging level
    # r_query_len: max len query history
    # **kwargs: Data to pass to each api module

    def __init__(self, server='http://localhost/zabbix', user=None,
                 passwd=None, timeout=10, r_query_len=10, **kwargs):
        """ Create an API object.  """
        self.server = server
        self.url = server + '/api_jsonrpc.php'
        self.proto = self.server.split("://")[0]
        #self.proto=proto
        self.httpuser = user
        self.httppasswd = passwd
        self.timeout = timeout

        for cls in ("usergroup", "user", "host", "item", "hostgroup",
                    "application", "trigger", "template", "action",
                    "alert", "info", "event", "graph", "graphitem",
                    "map", "screen", "script", "usermacro", "drule",
                    "history", "maintenance", "proxy", "apiinfo",
                    "configuration", "dcheck", "dhost", "discoveryrule",
                    "dservice", "iconmap", "image", "mediatype",
                    "service", "templatescreen", "usermedia"):
            setattr(self, cls,
                    ZabbixAPISubClass(self, dict(prefix=cls, **kwargs)))

        self.id = 0
        self.r_query = deque([], maxlen=r_query_len)
        LOG.debug("url: %s" % self.url)

    def recent_query(self):
        """
        return recent query
        """
        return list(self.r_query)

    def json_obj(self, method, params={}):
        obj = {
            'jsonrpc': '2.0',
            'method': method,
            'params': params,
            'auth': self.auth,
            'id': self.id,
        }
        ret = json.dumps(obj)
        LOG.debug("json_obj: " + ret)

        return ret

    def login(self, user='', password='', save=True):
        if user != '':
            l_user = user
            l_password = password

            if save:
                self.__username__ = user
                self.__password__ = password
        elif self.__username__ != '':
            l_user = self.__username__
            l_password = self.__password__
        else:
            raise ZabbixAPIException("No authentication information available.")

        # don't print the raw password.
        hashed_pw_string = "md5(" + hashlib.md5(l_password.encode('utf-8')).hexdigest() + ")"
        LOG.debug("Trying to login with %s:%s" %
                      (repr(l_user), repr(hashed_pw_string)))
        obj = self.json_obj('user.authenticate', {'user': l_user,
                                                  'password': l_password})
        result = self.do_request(obj)
        self.auth = result['result']

    def test_login(self):
        if self.auth != '':
            obj = self.json_obj('user.checkAuthentication', {'sessionid': self.auth})
            result = self.do_request(obj)

            if not result['result']:
                self.auth = ''
                return False  # auth hash bad
            return True  # auth hash good
        else:
            return False

    def do_request(self, json_obj):
        headers = {'Content-Type': 'application/json-rpc',
                   'User-Agent': 'python/zabbix_api'}

        if self.httpuser:
            LOG.info("HTTP Auth enabled")
            auth = 'Basic ' + string.strip(base64.encodestring(self.httpuser + ':' + self.httppasswd))
            headers['Authorization'] = auth
        self.r_query.append(str(json_obj))
        LOG.debug("Sending headers: " + str(headers))

        request = urllib2.Request(url=self.url, data=json_obj.encode('utf-8'), headers=headers)
        if self.proto == "https":
            https_handler = urllib2.HTTPSHandler(debuglevel=0)
            opener = urllib2.build_opener(https_handler)
        elif self.proto == "http":
            http_handler = urllib2.HTTPHandler(debuglevel=0)
            opener = urllib2.build_opener(http_handler)
        else:
            raise ZabbixAPIException("Unknow protocol %s" % self.proto)

        urllib2.install_opener(opener)
        response = opener.open(request, timeout=self.timeout)
        LOG.debug("Response Code: " + str(response.code))

        # NOTE: Getting a 412 response code means the headers are not in the
        # list of allowed headers.
        if response.code != 200:
            raise ZabbixAPIException("HTTP ERROR %s: %s"
                                     % (response.status, response.reason))
        reads = response.read()
        if len(reads) == 0:
            raise ZabbixAPIException("Received zero answer")
        try:
            jobj = json.loads(reads.decode('utf-8'))
        except ValueError as msg:
            LOG.error("unable to decode. returned string: %s" % reads)
            raise
        LOG.debug("Response Body: " + str(jobj))

        self.id += 1

        if 'error' in jobj:  # some exception
            msg = "Error %s: %s, %s while sending %s" % (jobj['error']['code'],
                    jobj['error']['message'], jobj['error']['data'], str(json_obj))
            if re.search(".*already\sexists.*", jobj["error"]["data"], re.I):  # already exists
                raise AlreadyExists(msg, jobj['error']['code'])
            else:
                raise ZabbixAPIException(msg, jobj['error']['code'])
        return jobj

    def logged_in(self):
        if self.auth != '':
            return True
        return False

    def api_version(self, **options):
        self.__checkauth__()
        obj = self.do_request(self.json_obj('APIInfo.version', options))
        return obj['result']

    def __checkauth__(self):
        if not self.logged_in():
            raise ZabbixAPIException("Not logged in.")


class ZabbixAPISubClass(ZabbixAPI):
    """ wrapper class to ensure all calls go through the parent object """
    parent = None
    data = None

    def __init__(self, parent, data, **kwargs):
        self.data = data
        self.parent = parent

        # Save any extra info passed in
        for key, val in kwargs.items():
            setattr(self, key, val)
            LOG.info("Set %s:%s" % (repr(key), repr(val)))

    def __getattr__(self, name):
        # workaround for "import" method
        if self.data["prefix"] == "configuration" and name == "import_":
            name = "import"

        def method(*opts):
            return self.universal("%s.%s" % (self.data["prefix"], name), opts[0])
        return method

    def __checkauth__(self):
        self.parent.__checkauth__()

    def do_request(self, req):
        return self.parent.do_request(req)

    def json_obj(self, method, param):
        return self.parent.json_obj(method, param)

    @dojson2
    @checkauth
    def universal(self, **opts):
        return opts
