#!/usr/bin/env python

import os
import sys
import uuid

from types import *

try:
    execfile('pyckman_config')
except:
    # Defaults
    PYCK_SAFE_INTERFACES = False
    PYCK_MODULE_GARBAGE_COLLECTOR = True
    PYCK_FORCE_DEPENDS = False
    PYCK_BOOTSTRAP_LOAD = []
    PYCK_FORCE_AT_LEAST_ONE = []
    PYCK_FORCE_ONLY_ONE = []

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
            self.__classes = {}

            # Absolute paths to registered modules
            self.__pycake_files = {}
            
            # Module Garbage collector
            self.__managed_modules = {}

        ### Un-managed modules operations ###
        # FIXME: not needed?
        def __get_all_loaded_modules(self):
            modules = []
            for item in globals().keys():
                if type(item) == ModuleType:
                    modules.append(item)
            return modules
       
        ### Modules operations ###
        # (Modules are passed as normal strings)

        def __load_module(self, module):
            try:
                exec('import ' + module)
            except:
                raise PyCakeImportError('Fail to import: ' + module)

        def __unload_module(self, module):
            if not PYCK_MODULE_GARBAGE_COLLECTOR:
                return
            try:
                exec('del(' + module + ')')
            except:
                raise PyCakeImportError('Fail to unload: ' + module)

        # FIXME: unused?
        def __unused_module_collector(self):
            unused = []
            for module in self.__managed_modules.keys():
                if self.__managed_modules[module] <= 0:
                    unused.append(module)
            for module in unused:
                self.__unload_module(module)
                del(self.__managed_modules[module])

        def managed_import(self, module):
            # Already loaded?
            if module in self.__managed_modules.keys():
                self.__managed_modules[module] += 1
                return
            self.__load_module(module)
            self.__managed_modules[module] = 1

        def managed_unimport(self, module):
            if module in self.__managed_modules.keys():
                self.__managed_modules[module] -= 1
                if self.__managed_modules[module] == 0:
                    self.__unload_module(module)
                return
            raise PyCakeImportError('Try to unload not loaded module: ' +
                                    module)
            
        ### Classes operations ###

        def __unload_class(self, class_name):
            try:
                if type(class_name) in StringTypes:
                    exec('del(' + class_name + ')')
                else:
                    del(class_name)
                return True
            except:
                return False

        def __get_class_from_name(self, class_name):
            if type(class_name) in StringTypes:
                for pycake in self.__classes.keys():
                    for single_class in self.__classes[pycake]:
                        if class_name == single_class.__name__:
                            return single_class

        def __get_all_loaded_classes(self):
            classes = []
            for item in globals().keys():
                if type(item) == ClassType:
                    classes.append(item)
            return classes

        ### Basic pycakes operations ###

        def __get_capabilities_of(self, pycake_file):
            if not os.path.isfile(pycake_file):
                raise BadPyCake('File not found: ' + pycake_file)

            global _get_capabilities
            global _get_extended_capabilities
            _get_capabilities = None
            _get_extended_capabilities = None
            try:
                execfile(pycake_name, globals())
                if not callable(_get_capabilities):
                    raise BadPlugin('"get_capabilities()" mandatory method not found in PyCake: ' + pycake_name)
                caps = _get_capabilities()
                if not callable(_get_extended_capabilities):
                    extra_caps = {}
                else:
                    extra_caps = _get_extended_capabilities()

                # Clear classes
                if not caps.has_key('main_class'):
                    raise BadPlugin('Mandatory key "main_class" not found in PyCake caps: ' + pycake_name)
                self.__del_class(caps['main_class'])

                # Clear Exceptions
                if extra_caps.has_key('exceptions'):
                    for single_exception in extra_caps['exceptions']:
                        self.__del_class(single_exception)

                # Clear aux. classes
                if extra_caps.has_key('alternates'):
                    for single_class in extra_caps['alternates']:
                        self.__del_class(single_class)
            except:
                raise BadPyCake('Unknown exception: ' + sys.last_traceback)
            return caps.update(extra_caps)

        def __load_pycake_space(self, pycake_file):
            global _load
            _load = None
            try:
                execfile(pycake_name, globals())
                # Pre-load
                if callable(_load):
                    result = _load()
                else:
                    result = True
                # Clear plugin space
                _load = None
                _unload = None
                _get_capabilities = None
                _get_extended_capabilities = None
                return retvalue
            except:
                raise BadPyCake('Unknown exception during load of ' +
                                pycake_name + '(' + sys.last_traceback + ')')

        def load_pycake(self, pycake_id):
            if not pycake_id in self.__pycake_file.keys():
                raise UnregisteredPyCake('Try to load unregistered pycake (' +
                                         str(pycake_id) + ')')

            # FIXME: *** Test for pycake depends!!! ***

            # Import needed modules
            if caps.has_key('modules'):
                for module in caps['modules']:
                    self.managed_import(module)
            # Load classes
            if self.__load_pycake_space(self.__pycake_file[pycake_id]):
                # Refresh class map
                caps = self.__registry[pycake_id]
                self.__classes[pycake_id] = [caps['main_class']]
                if caps.has_key('alternates'):
                    self.__classes[pycake_id] += caps['alternates']
                if caps.has_key('exceptions'):
                    self.__classes[pycake_id] += caps['exceptions']
                return True
            else:
                # Unload modules
                if caps.has_key('modules'):
                    for module in caps['modules']:
                        self.managed_unimport(module)
                # FIXME: raise an exception? unload classes?
                return False
            
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



