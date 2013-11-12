#!/usr/bin/env python
# encoding: utf-8
'''
app_manager -- Generic app manager for hydra

The app manager is in charge of check and monitor one or several servers and update the status information at one or several Hydra Servers using the restful server AP.

The basic functionality is to notify to one Hydra Server when an application is Started, Stopping, or Removed. In addition, it will provide information about the server health status like CPU and memory usage and any useful information like the size of the server or the prefered balance strategy.

All these information should be updated periodically. If not, the Hydra server will assume that the servers are shutted down.

@author:     German Ramos Garcia
'''

import time
import sys
import os
import json
import logging
from logging.config import fileConfig   
from optparse import OptionParser
import urllib2
import ConfigParser
from urlparse import urlparse

__all__ = []
__version__ = 1.0
__date__ = '2013-05-29'
__updated__ = '2013-05-29'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

INFO_TIMEOUT = 5

class stateEnum:
    READY = 0
    UNAVAILABLE = 1
      
def main(argv=None):
    '''Command line options.'''
    
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.1"
    program_build_date = "%s" % __updated__
 
    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_longdesc = '''''' # optional - give further explanation about what the program does
    program_license = "Copyright 2013 - BBVA"
 
    if argv is None:
        argv = sys.argv[1:]
    try:
        # setup option parser
        parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
        parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")
        parser.add_option("-c", "--config", default="app_manager.cfg", dest="configFile", action="store", help="set configuration file [default: %default]")
        parser.add_option("-l", "--log-config", default="logging.cfg", dest="loginConfigFile", action="store", help="set log configuration file [default: %default]")

        # process options
        (opts, _args) = parser.parse_args(argv)
        
        if opts.verbose > 0:
            print("verbosity level = %d" % opts.verbose)
        
        config = ConfigParser.ConfigParser()
        #config.read(['app_manager.cfg', os.path.expanduser('~/app_manager.cfg'), '/etc/app_manager.cfg'])
        print "Using config file " + opts.configFile;
        config.read([opts.configFile])
        
        #Conf logging
        fileConfig(opts.loginConfigFile)
        fileHandler = logging.handlers.RotatingFileHandler(opts.configFile + ".log", mode='a', maxBytes=1048576, backupCount=3)
        fileHandler.setFormatter("simpleFormatter")
        logging.getLogger().addHandler(fileHandler)
        print "Logging to " + opts.configFile + ".log";
        
        # MAIN BODY #
        while True:
            try:
                servers = {}
                logging.debug("*** BEGIN ITERATION ***")
                for key,server in config.items("SERVERS"):
                    server_public,server_private = server.split(",")
                    server_public_fragments = urlparse(server_public)
                    server_key = server_public_fragments.netloc
                    logging.debug("Getting info from " + server_private)
                    try:
                        response = urllib2.urlopen(server_private, timeout=INFO_TIMEOUT)
                        output = json.load(response)
                        state = int(output["state"])
                        cpuLoad = float(output["cpuLoad"])
                        memLoad = float(output["memLoad"])
                    except Exception, e:
                        logging.error("Exception: " + str(e))
                        state = stateEnum.UNAVAILABLE
                        cpuLoad = 0
                        memLoad = 0
                    #Create server status object and append to the server list
                    timestamp = int(round(time.time() * 1000))
                    server_item = {
                        "server": server_public,
                        "cost": int(config.get("MAIN", "cost")),
                        "cloud": config.get("MAIN", "cloud"),
                        "status": {
                               "cpuLoad": cpuLoad,
                               "memLoad": memLoad,
                               "timeStamp": timestamp,
                               "stateEvents": {
                                   timestamp: state
                               }
                           }
                    }
                    logging.debug(server_item)
                    servers[server_key] = server_item
                #End servers for
                timestamp = int(round(time.time() * 1000))
                localStrategyEvents = {
                                         timestamp: config.get("MAIN", "local_strategy")
                }
                cloudStrategyEvents = {
                                         timestamp: config.get("MAIN", "cloud_strategy")
                }
                data = {
                        "localStrategyEvents": localStrategyEvents,
                        "cloudStrategyEvents": cloudStrategyEvents,
                        "servers": servers
                }
                answer = json.dumps(data)
                logging.debug("Data to post:")
                logging.debug(answer)
                #POST
                for key,hydra in config.items("HYDRAS"):
                    logging.debug("Posting to " + hydra)                   
                    opener = urllib2.build_opener(urllib2.HTTPHandler)
                    request = urllib2.Request(hydra + "/app/" + config.get("MAIN", "app_id"), answer)
                    request.add_header("content-type", "application/json")
                    #request.get_method = lambda: 'POST'
                    url = opener.open(request)
                    if url.code != 200:
                        logging.error("Error connecting with hydra {0}: Code: {1}".format(hydra,url.code))
                    else:
                        logging.debug("Posted OK")
            except Exception, e:
                logging.error("Exception: " + str(e))
            time.sleep(config.getint("MAIN", "sleep_time"));
        
    except Exception, e:
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2


if __name__ == "__main__":
    if DEBUG:
        sys.argv.append("-v")
        logging.getLogger("root").setLevel(logging.DEBUG)
    else:
        sys.argv.append("-v")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'app_manager_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())