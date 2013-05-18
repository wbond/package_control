import logging

'''
Warpper for the python logging module.
by @blopker
'''

def init(debug=False):
    ''' Initializes the root logger for the
        rest of this program's execution.
        All children loggers will assume the
        root's log level if theirs is not set'''
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO,
                            format="Package Control: %(message)s")
    # Not shown if debug=False
    log.debug("Logger initialized.")

def get(name):
    ''' Get a new named logger. Usually called like: logger.get(__name__).
    Wraps the getLogger method so you don't have to import two modules.'''
    return logging.getLogger(name)

def isDebug():
    ''' Returns True if debugging is enabled. '''
    return log.getEffectiveLevel() == logging.DEBUG

# Needs to be at the bottom here so get() is defined first.
log = get(__name__)
