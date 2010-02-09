#!/usr/bin/env python

import os
import sys
import uuid

from types import *

try:
    execfile('pyckman_config')
except:
    # Defaults
    pass

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

class PyCakeImportError(Exception):
    def __init__(self, inf):
        Exception.__init__(self, inf)
        self.__inf = inf

        def __str__(self):
            return repr(self.__inf)

class PyCakeClassesError(Exception):
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

            # Absolute paths to registered modules
            self.__pycake_files = {}
            
            # Garbage collector
            self.__managed_modules = {}

            self.__managed_classes = {}

        ### Modules operations ###

        # Modules are passed as normal strings
        def __load_module(self, module):
            try:
                exec('import ' + module)
            except:
                raise PyCakeImportError('Fail to import: ' + module)
            return True

        def __unload_module(self, module):
            try:
                exec('del(' + module + ')')
            except:
                raise PyCakeImportError('Fail to unload: ' + module)
            return True

        def __get_all_loaded_modules(self):
            modules = []
            for item in globals().keys():
                if type(item) == ModuleType:
                    modules.append(item)
            return modules
        
        def __unused_module_collector(self):
            unused = []
            for module in self.__managed_modules.keys():
                if self.__managed_modules[module] <= 0:
                    unused.append(module)
            for module in unused:
                self.__unload_module(module)
                del(self.__imodules[module])

        ### Managed Classes operations ###

        def __get_class_from_name(self, class_name):
            if type(class_name) in StringTypes:
                for loaded_class in self.__managed_classes.keys():
                    if loaded_class.__name__ == class_name:
                        return loaded_class

        def __refresh_loaded_classes(self, classes):
            if type(classes) == ListType:
                for loaded_class in classes:
                    if not self.__managed_classes.has_key(loaded_class):
                        self.__managed_classes[loaded_class] = 0
                    self.__managed_classes[loaded_class] += 1
            else:
                if not self.__managed_classes.has_key(classes):
                    self.__managed_classes[classes] = 1
                else:
                    self.__managed_classes[classes] += 1

        def __refresh_unloaded_classes(self, classes):
            if type(classes) == ListType:
                for loaded_class in classes:
                    if not self.__managed_classes.has_key(loaded_class):
                        raise PyCakeClassesError('Request to unload unmanaged class: ' + repr(loaded_class))
                    self.__managed_classes[loaded_class] -= 1
            else:
                if not self.__managed_classes.has_key(classes):
                    raise PyCakeClassesError('Request to unload unmanaged class: ' + repr(classes))
                self.__managed_classes[classes] -= 1

        def __unused_classes_collector(self):
            unused = []
            for managed_class in self.__managed_classes.keys():
                if self.__managed_classes[managed_class] <= 0:
                    unused.append(managed_class)
            for managed_class in unused:
                del(managed_class)
                del(self.__managed_classes[managed_class])

        def __get_all_loaded_classes(self):
            classes = []
            for item in globals().keys():
                if type(item) == ClassType:
                    classes.append(item)
            return classes

        ### Basic pycakes operations ###

        # TODO: FIXME: BUG: #
        def __get_capabilities_of(self, pycake_file):
            pass

        # TODO: FIXME: BUG: #
        def __get_extended_capabilities_of(self, pycake_file):
            pass

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



