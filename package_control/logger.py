import logging
from logging import StreamHandler, Formatter

'''
Warpper of the python logging module for Sublime Text plugins.
by @blopker
'''

log = False

def init(name, debug=True):
    ''' Initializes the named logger for the
        rest of this program's execution.
        All children loggers will assume this
        loggers's log level if theirs is not set'''

    global log

    if log != False:
        # Logger already initialized.
        return

    log = logging.getLogger(name)
    handler = StreamHandler()

    plugin_name = name.split('.')[0]

    if debug:
        log.setLevel(logging.DEBUG)
        handler.setFormatter(_getDebugFmt(plugin_name))
    else:
        log.setLevel(logging.INFO)
        handler.setFormatter(_getFmt(plugin_name))

    log.addHandler(handler)

    # Not shown if debug=False
    log.debug("Logger for %s initialized.", plugin_name)

def _getDebugFmt(plugin_name):
    fmt = '%(levelname)s:' + plugin_name + '.%(module)s: %(message)s'
    return Formatter(fmt=fmt)

def _getFmt(plugin_name):
    fmt = plugin_name + ': %(message)s'
    return Formatter(fmt=fmt)

def get(name):
    ''' Get a new named logger. Usually called like: logger.get(__name__).
    Wraps the getLogger method so you don't have to import two modules.'''
    return logging.getLogger(name)

def isDebug():
    ''' Returns True if debugging is enabled. '''
    return log.getEffectiveLevel() == logging.DEBUG
