#!/usr/bin/env python

import os
import sys
import uuid

execfile('pyckman_config')

global _load
global _unload
global _get_capabilities
global _get_extendended_capabilities

class BadPyCake(Exception):
    def __init__(self, inf):
        Exception.__init__(self, inf)
        self.__inf = inf

        def __str__(self):
            return repr(self.__inf)

class UnregisteredPyCake(Exception):
    def __init__(self, inf):
        Exception.__init__(self, inf)
        self.__inf = inf

        def __str__(self):
            return repr(self.__inf)

def get_pycake_caps(pycake_name):
    if not os.path.isfile(pycake_name):
        raise BadPyCake('File not found: ' + pycake_name)

    global _get_capabilities
    global _get_extended_capabilities
    _get_capabilities = None
    _get_extended_capabilities = None

    try:
        execfile(pycake_name, globals())
        if not callable(_get_capabilities):
            raise BadPlugin('"get_capabilities()" method not found in PyCake: '
                            + pycake_name)
        caps = _get_capabilities()
        if callable(_get_extended_capabilities):
            extra_caps = _get_extended_capabilities()
        else:
            extra_caps = {}

        # Clear classes
        if not caps.has_key('main_class'):
            raise BadPlugin('Mandatory key "main_class" not found in PyCake: '
                            + pycake_name)
        del(caps['main_class'])
        if extra_caps.has_key('exceptions'):
            for single_exception in extra_caps['exceptions']:
                del(single_exception)
        if extra_caps.has_key('alternates'):
            for single_class in extra_caps['alternates']:
                del(single_class)
    except:
        raise BadPyCake('Unknown exception: ' + sys.last_traceback)
    return (caps, extra_caps)

def load_pycake(plug_name):
    if not valid_plugin(plug_name):
        raise BadPlugin('Not a valid plugin: ' + plug_name)
    global _load
    global _get_capabilities
    global _get_extended_capabilities
    _load = None
    execfile(plug_name, globals())
    retvalue = _load()

    # Clear plugin space
    # (keep main_class and _get_capabilities)
    _load = None
    _unload = None

    return retvalue

def unload_pycake(plug_name):
    if not valid_plugin(plug_name):
        raise BadPlugin('Not a valid plugin: ' + plug_name)
    global _unload
    global _get_capabilities
    _unload = None
    execfile(plug_name, globals())
    retvalue = _unload()

    # Clear plugin space
    caps = _get_capabilities()
    del(caps['main_class'])
    del(caps)
    _get_capabilities = None
    _load = None
    _unload = None
    
    return retvalue
             
def valid_pycake(plug_name):
    retvalue = True
    if not os.path.isfile(plug_name):
        return False
    global _get_capabilities
    global _load
    global _unload
    _get_capabilities = None
    _load = None
    _unload = None
    # Load plugin space
    execfile(plug_name, globals())
    if (not callable(_load) or
        not callable(_unload) or
        not callable(_get_capabilities)):
        retvalue = False
    
    # Plugin looks like a valid plugin,
    # Now test for bad capabilities
    caps = {}
    if (callable(_get_capabilities)):
        caps = _get_capabilities()
        if (not caps.has_key('name') or
            not caps.has_key('maj_ver') or
            not caps.has_key('min_ver') or
            not caps.has_key('build') or
            not caps.has_key('main_class') or
            not caps.has_key('type') or
            not caps.has_key('priority')):
            retvalue = False
        if not caps['type'] in DESCRIPTION.keys():
            retvalue = False

    # Clear plugin space
    if (caps.has_key('main_class')):
        del(caps['main_class'])
    del(caps)
    _get_capabilities = None
    _load = None
    _unload = None

    return retvalue

def search_plugins(path):
    dirList = os.listdir(path)
    plugins = []
    for file_name in dirList:
        # Get plugins by filename
        (dir_name, f_name) = os.path.split(file_name)
        if f_name.startswith('plugin_') and f_name.endswith('.py'):
            plugins.append(f_name)

    ret_val = []
    for valid in plugins:
        if valid_plugin(os.path.join(path, valid)):
            ret_val.append(valid)
    return ret_val

# Pycake Manager (singleton)
class PycakeManager(object):
    __manager = None
    class Implementation:
        def __init__(self):
            self.__registry = {}
            self.__loaded = {}

            self.__pycake_file = {}
            self.__instances = {}

            self.__modules_instances = {
                'os' : 1,
                'sys' : 1,
                'uuid' : 1
                }

        def __uuid_of(pycake_file):
            files = dict([(v, k) for (k, v) in self.__pycake_file.iteritems()])
            if file.has_key(pycake_id):
                return files[pycake_file]
            raise UnregisteredPyCake('PyCake "' + pycake_file +
                                     '" is unregistered.')

        def __add_single_pycake(pycake_file):
            if pycake_file in self.__pycake_file.values():
                # Already registered, return it
                return self.__uuid_of(pycake_file)

            new_uuid = uuid.uuid4()
            try:
                self.__registry[new_uuid] = get_pycake_caps(pycake_name)
                self.__pycake_files[new_uuid] = pycake_file
                self.__loaded[new_uuid] = False
            except:
                return None
            return new_uuid

        # Register single or multiple pycakes
        def add_pycakes_to_registry(pycakes):
            if type(pycakes).__name__ == 'list':
                new_ids = []
                for pycake in pycakes:
                    new_ids.append(self.__add_single_pycake(pycake))
                return new_ids
            return self.__add_single_pycake(pycake)

        # 
        def register(self, plugin):
            global _get_capabilities
            if load_plugin(plugin):
                # Plugin loaded succesfully
                new_uuid = uuid.uuid4()
                self.__registry[new_uuid] = _get_capabilities()
                self.__plugnames[new_uuid] = plugin
                # Create first instance
                self.__instances[new_uuid] = _get_capabilities()['main_class']()
                return new_uuid
            # Plugin not registered
            return None

        def unregister(self, uuid):
            if (self.__registry.has_key(uuid)):
                # Unregister plugin
                del(self.__instances[uuid])
                del(self.__registry[uuid])
                name = self.__plugnames[uuid]
                del(self.__plugnames[uuid])
                # Call _unload and clear plugin space
                return unload_plugin(name)
            # Plugin not registered
            return False

        def get_registered(self):
            return self.__registry.keys()

        def is_registered(self, uuid):
            return uuid in self.get_registered()

        def is_any_of_type(self, plug_type):
            for plugin in self.get_registered():
                capabilities = self.__registry[plugin]
                if capabilities['type'] == plug_type:
                    return True
            return False

        def get_of_type(self, plug_type):
            available = []
            for plugin in self.get_registered():
                capabilities = self.__registry[plugin]
                if capabilities['type'] == plug_type:
                    available.append(plugin)
            return available

        def __getBest(self, plug_type):
            priority = -1
            best = None
            for plugin in self.get_of_type(plug_type):
                capabilities = self.__registry[plugin]
                if (capabilities['priority'] > priority):
                    priority = capabilities['priority']
                    best = plugin
            return best

        def get_instance_of(self, uuid):
            if self.is_registered(uuid):
                return self.__instances[uuid]
            return None

        def get_instance_of_type(self, plug_type):
            return self.get_instance_of(self.__getBest(plug_type))

    def __init__(self):
        if not PluginManager.__manager:
            PluginManager.__manager = PluginManager.Implementation()

    def __getattr__(self, aAttr):
        return getattr(self.__manager, aAttr)

    def __setattr__(self, aAttr, aValue):
        return setattr(self.__manager, aAttr, aValue)
            
if __name__ == '__main__':
    pman = PluginManager()
    print search_plugins('plugins/')
    if pman.register('plugins/plugin_dummy.py'):
        print 'Sucessfully registered!'
    else:
        print 'Error registering plugin'
    print 'pman1 registered:', pman.get_registered()
    pman2 = PluginManager()
    print 'pman2 registered:', pman2.get_registered()
    print 'MAIN plugins:', pman.get_of_type(MAIN)
    a = pman.get_instance_of_type(MAIN)
    a.sayHello()
    for p in pman.get_registered():
        if pman.unregister(p):
            print 'Sucessfully unregistered!'
        else:
            print 'Error unregistring plugin'
    print 'OK'



