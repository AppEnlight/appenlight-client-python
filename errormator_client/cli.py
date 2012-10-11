from __future__ import with_statement
import os
import pkg_resources
import sys
from errormator_client import client
import logging
logging.basicConfig()

cwd = os.getcwd()


class CommandRouter(object):

    @classmethod
    def makeini(cls, ini_name):
        while True:
            print '\nCurrent directory: %s' % cwd
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
                print '\nFile %s already exists' % ini_path
            else:
                ini_str = pkg_resources.resource_string('errormator_client',
                                        'templates/default_template.ini')
                with open(ini_path, 'w') as f:
                    f.write(ini_str)
                print '\nCreated new errormator client config: %s' % ini_path
                print 'REMEMBER TO UPDATE YOUR API KEY IN INI FILE'

        print "\n\nFinished"

    @classmethod
    def testini(cls, ini_name):
        print '\nCurrent directory: %s' % cwd
        ini_path = os.path.join(cwd, ini_name)
        config = client.get_config(path_to_config=ini_path)
        print 'INI file read - creating client'
        errormator_client = client.Client(config)
        print 'Client created, sending test entry'
        record = logging.makeLogRecord({'name': 'errormator.client.test',
                                'message': 'Test entry'})

        errormator_client.py_log({}, [record])
        result = errormator_client.submit_data()
        if not result['logs']:
            print 'something went wrong, please check your API key'
        else:
            print 'Test entry transmitted correctly'

    @classmethod
    def pserve(self, *args, **kwargs):
        argv = sys.argv
        quiet = False
        ini_path = os.environ.get('ERRORMATOR_INI')
        config = {}
        if not ini_path:
            print "ERRORMATOR_INI variable is missing from environment/run cmd"
        else:
            config = client.get_config(path_to_config=ini_path)
        if not config.get('errormator'):
            print 'WARNING Could not instantiate the client properly'
        else:
            client.Client(config)
        from pyramid.scripts import pserve
        command = pserve.PServeCommand(argv[1:], quiet=quiet)
        return command.run()


def cli_start():
    args = sys.argv
    if len(args) < 2:
        print """
    Possible commands
    makeini [ERRORMATOR_INI_NAME] - creates new config file for errormator

    testini [ERRORMATOR_INI_NAME] - sends a test log entry to test your API key

    pserve  [APP_CONFIG.ini]      - ensures errormator client decorates all
                                    libs before pyramid's pserve command is
                                    executed, use instead normal pserve command
        """
        return
    command = args[1]
    command_args = args[2:]
    e_callable = getattr(CommandRouter, command, None)
    if not e_callable:
        print 'There is no command like %s' % command
    else:
        callable(*command_args)
