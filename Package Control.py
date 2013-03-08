import sublime
import sys


st_version = 2

# Warn about out-dated versions of ST3
if sublime.version() == '':
	st_version = 3
	print('Package Control: Please upgrade to Sublime Text 3 build 3012 or newer')

elif int(sublime.version()) > 3000:
	st_version = 3


mod_prefix = 'package_control'

# ST3 loads each package as a module, so it needs an extra prefix
if st_version == 3:
	mod_prefix = 'Package Control.' + mod_prefix

# Make sure all dependencies are reloaded on upgrade
pc_modules = list()
for mod_name in sys.modules:
	if mod_name.startswith(mod_prefix):
		pc_modules.append(mod_name)

for mod_name in pc_modules:
	sys.modules.pop(mod_name)
del pc_modules


try:
	# Python 3
	from .package_control.commands import *
	from .package_control.package_cleanup import PackageCleanup

except (ValueError):
	# Python 2
	from package_control import sys_path

	from package_control.commands import *
	from package_control.package_cleanup import PackageCleanup


def plugin_loaded():
	# Start shortly after Sublime starts so package renames don't cause errors
	# with keybindings, settings, etc disappearing in the middle of parsing
	sublime.set_timeout(lambda: PackageCleanup().start(), 2000)

if st_version == 2:
	plugin_loaded()
