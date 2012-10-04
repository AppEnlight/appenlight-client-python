from __future__ import with_statement
import os
import pkg_resources
from optparse import OptionParser
from errormator_client import client
import logging
logging.basicConfig()

cwd = os.getcwd()

class CommandRouter(object):   
    
    @classmethod
    def makeini(cls, ini_name):
        while True:
            print '\nCurrent directory: %s' % cwd
            question = '\nThere is no ini file in current directory, create one? y/n: '
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
            
        print "\n\nFinished"
    
    @classmethod
    def testini(cls, ini_name):
        print '\nCurrent directory: %s' % cwd
        ini_path = os.path.join(cwd, ini_name)
        config = client.get_config(path_to_config=ini_path)
        print 'INI file read - creating client'
        errormator_client = client.Client(config)
        print 'Client created, sending test entry'
        record = logging.makeLogRecord({'name':'errormator.client.test',
                                'message':'Test entry'})
        
        errormator_client.py_log({}, [record])
        result = errormator_client.submit_data()
        if not result['logs']:
            print 'something went wront, please check your API key'
        else:
            print 'Test entry transmitted correctly'
        
        

def cli_start():
    parser = OptionParser()
    (options, args) = parser.parse_args()
    command = args[0]
    command_args = args[1:]
    callable = getattr(CommandRouter, command, None)
    if not callable:
        print 'There is no command like %s' % command
    else:
        callable(*command_args)
