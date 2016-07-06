from __future__ import with_statement, print_function
import os
import pkg_resources
import sys
from appenlight_client import client
import logging

logging.basicConfig()

cwd = os.getcwd()


class CommandRouter(object):
    @classmethod
    def makeini(cls, ini_name):
        while True:
            print('\nCurrent directory: %s' % cwd)
            question = '''\nThere is no ini file in current directory,
                        create one? y/n: '''
            confirm = raw_input(question).lower()
            if confirm and confirm in ['y', 'yes']:
                confirm = True
                break
            elif confirm in ['n', 'no']:
                confirm = False
                break
        if confirm:
            ini_path = os.path.join(cwd, ini_name)
            exists = os.path.exists(ini_path)
            if exists:
                print('\nFile %s already exists' % ini_path)
            else:
                ini_str = pkg_resources.resource_string(
                    'appenlight_client',
                    'templates/default_template.ini')
                with open(ini_path, 'w') as f:
                    if client.PY3:
                        f.write(ini_str.decode('utf8'))
                    else:
                        f.write(ini_str)
                print('\nCreated new appenlight client config: %s' % ini_path)
                print('REMEMBER TO UPDATE YOUR API KEY IN INI FILE')

        print("\n\nFinished")

    @classmethod
    def testini(cls, ini_name):
        print('\nCurrent directory: %s' % cwd)
        ini_path = os.path.join(cwd, ini_name)
        config = client.get_config(path_to_config=ini_path)
        print('INI file read - creating client')
        appenlight_client = client.Client(config)
        print('Client created, sending test entry')
        logging.error('This is a test entry', extra={'sometag': 'appenlight.client.test',
                                                     'foo': 'bar'})
        records = appenlight_client.log_handlers_get_records()
        appenlight_client.py_log({}, records)
        result = appenlight_client.transport.send(appenlight_client.transport.log_queue[:], 'logs')
        if not result:
            print('something went wrong, please check your API key')
            return False
        else:
            print('Test entry transmitted correctly')
        return True

    @classmethod
    def pserve(self, *args, **kwargs):
        argv = sys.argv
        quiet = False
        ini_path = os.environ.get('APPENLIGHT_INI')
        config = {}
        if not ini_path:
            print("APPENLIGHT_INI variable is missing from environment/run cmd")
        else:
            config = client.get_config(path_to_config=ini_path)
        if not config.get('appenlight'):
            print('WARNING Could not instantiate the client properly')
        else:
            client.Client(config)
        from pyramid.scripts import pserve

        command = pserve.PServeCommand(argv[1:], quiet=quiet)
        return command.run()


def cli_start():
    args = sys.argv
    if len(args) < 2:
        print ("""
    Possible commands
    makeini [APPENLIGHT_INI_NAME] - creates new config file for appenlight

    testini [APPENLIGHT_INI_NAME] - sends a test log entry to test your API key

    pserve  [APP_CONFIG.ini]      - ensures appenlight client decorates all
                                    libs before pyramid's pserve command is
                                    executed, use instead normal pserve command
        """)
        return
    command = args[1]
    command_args = args[2:]
    e_callable = getattr(CommandRouter, command, None)
    if not e_callable:
        print('There is no command like %s' % command)
    else:
        e_callable(*command_args)
