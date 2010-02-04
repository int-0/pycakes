#!/usr/bin/env python
#
import plugman
import os
import sys

PLUGIN_PATH = 'plugins/'

def bootstrap(pmanager):
    # Get available plugins
    availables = plugman.search_plugins(PLUGIN_PATH)

    # Search for ANY LOGGER plugin (the best)
    logger = None
    priority = -1
    for plugin in availables:
        caps = plugman.get_plugin_capabilities(os.path.join(PLUGIN_PATH, plugin))
        if (caps['type'] == plugman.LOGGER):
            if (caps['priority'] > priority):
                logger = plugin
                priority = caps['priority']
    if not logger:
        print 'BOOTSTRAP ERROR: need at least one logger plugin!'
        sys.exit(1)
    if pmanager.register(os.path.join(PLUGIN_PATH, logger)):
        log = pmanager.get_instance_of_type(plugman.LOGGER)
        log.msg('Bootstrap initzialized!')
        log.msg('Loading main plugins...')
    else:
        print 'BOOTSTRAP ERROR: cannot register logger plugin!'
        sys.exit(1)

    # Load all MAIN plugins
    for plugin in availables:
        caps = plugman.get_plugin_capabilities(os.path.join(PLUGIN_PATH, plugin))
        if (caps['type'] == plugman.MAIN):
            version = 'v' + str(caps['maj_ver']) + '.' + str(caps['min_ver']) + '.' + str(caps['build'])
            log.msg_('Registering ' + caps['name'] + ' ' + version + '...')
            if pmanager.register(os.path.join(PLUGIN_PATH, plugin)):
                log.msg('OK!')
            else:
                log.msg('ERROR!')

    # Load UI plugin
    ui = None
    priority = -1
    for plugin in availables:
        caps = plugman.get_plugin_capabilities(os.path.join(PLUGIN_PATH, plugin))
        if (caps['type'] == plugman.UI):
            if (caps['priority'] > priority):
                ui = plugin
                priority = caps['priority']
    if not ui:
        print 'BOOTSTRAP ERROR: need at least one user interface plugin!'
        sys.exit(1)

    log.msg('Bootstrap ended!')
