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
        help="zabbix server URL")
    parser.add_argument(
        "--username", "-u", default="Admin",
        help="username (will prompt if not given)")
    parser.add_argument(
        "--password", "-p", default="zabbix",
        help="password (will prompt if not given)")
    parser.add_argument(
        "--indent", "-i", default=False,
        action="store_true", help="indent JSON responce")
    parser.add_argument(
        "--debug", "-d", default=False,
        action="store_true", help="debug")
    parser.add_argument(
        "--expression", "-e", default=None,
        help="JSON expression to execute")
    parser.add_argument(
        "--file", "-f", default=None,
        help="JSON file to execute")
    parser.add_argument(
        "--keep-going", "-k", default=False,
        action="store_true",
        help="continue execution if some commands have failed")
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
    sys.exit(1)


def die(msg):
    print >> sys.stderr, msg
    sys.exit(1)


def main():
    handler = logging.StreamHandler(sys.stderr)
    LOG = logging.getLogger()
    LOG.addHandler(handler)

    options = get_options()

    LOG.setLevel(logging.DEBUG if options.debug else logging.INFO)

    zapi = ZabbixAPI(server=options.server)

    try:
        json_data = (json.load(open(options.file, "r")) if options.file
                     else json.loads(options.expression))
        zapi.login(options.username, options.password)
    except Exception as e:
        die(str(e))

    def execute_command(js):
        try:
            cls, method = js["method"].split(".", 1)
        except:
            print >> sys.stderr, "missing method name"
            return False
        try:
            obj = getattr(zapi, cls)
        except:
            print >> sys.stderr, "class %s not found" % cls
            return False
        try:
            print json.dumps(
                getattr(obj, method)(js.get("params", {})),
                **({"indent": 4} if options.indent else {}))
        except Exception as e:
            print >> sys.stderr, str(e)
            return False
        return True

    if isinstance(json_data, list):
        for i in json_data:
            if not (execute_command(i) or options.keep_going):
                sys.exit(1)
    else:
        if not execute_command(json_data):
            sys.exit(1)


if  __name__ == "__main__":
    main()
