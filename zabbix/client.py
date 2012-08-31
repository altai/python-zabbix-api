#!/usr/bin/python2
import argparse
import json
import logging
import sys
from getpass import getpass
from zabbix.api import ZabbixAPI, ZabbixAPIException


def get_options():
    """ command-line options """

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--server", "-s", default="http://localhost/zabbix",
        help="Zabbix Server URL (REQUIRED)")
    parser.add_argument(
        "--username", "-u", default="Admin",
        help="Username (Will prompt if not given)")
    parser.add_argument(
        "--password", "-p", default="zabbix",
        help="Password (Will prompt if not given)")
    parser.add_argument(
        "--indent", "-i", default=False,
        action="store_true", help="indent JSON responce")
    parser.add_argument(
        "--debug", "-d", default=False,
        action="store_true", help="indent JSON responce")
    parser.add_argument(
        "json", nargs=1,
        help="JSON to execute, including 'method' key")
    options = parser.parse_args()

    if not options.server:
        show_help(parser)

    if not options.username:
        options.username = raw_input('Username: ')

    if not options.password:
        options.password = getpass()

    # apply clue to user...
    if not options.username and not options.password:
        show_help(parser)

    return options


def show_help(p):
    p.print_help()
    sys.exit(-1)


def die(msg):
    print >> sys.stderr, msg
    sys.exit(-1)


def main():
    handler = logging.StreamHandler(sys.stderr)
    LOG = logging.getLogger()
    LOG.addHandler(handler)

    options = get_options()

    LOG.setLevel(logging.DEBUG if options.debug else logging.INFO)

    zapi = ZabbixAPI(server=options.server)

    try:
        json_data = json.loads(options.json[0])
        cls, method = json_data["method"].split(".", 1)
        params = json_data["params"]
        zapi.login(options.username, options.password)
    except Exception as e:
        die(str(e))
    try:
        obj = getattr(zapi, cls)
    except:
        die("class %s not found" % cls)
    print json.dumps(
        getattr(obj, method)(params),
        **({"indent": 4} if options.indent else {}))


if  __name__ == "__main__":
    main()
