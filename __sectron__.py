import os, sys

def __import__(pathe):
	directory, module_name = os.path.split(pathe)
	module_name = os.path.splitext(module_name)[0]

	path = list(sys.path)
	sys.path.insert(0, directory)
	try:
		module = __import__(module_name)
	finally:
		sys.path[:] = path
