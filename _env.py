# IMPORTANT: Import this first, before anything else
#
# (Specifically, it needs to be imported before anything in _lib is accessed)
#

# Find the nearest _lib folder for imports. If none found, use BIPYLIB environment variable
# if present.
import sys, os
# import relative to calling script
d = os.path.abspath(os.path.join(os.path.dirname(__file__),'_lib')); d2 = None
while not os.path.exists(d):
	d2 = d; d = os.path.join(os.path.dirname(os.path.dirname(d)), '_lib')
	if d == d2:
		if os.environ.get('BIPYLIB'):
			d = os.environ.get('BIPYLIB')
		else:
			raise SystemExit('Could not find "_lib" folder in any parent folder')
sys.path.append(d); os.environ['PATH'] += ';'+d

# Point to the root dir
root = os.path.dirname(d)

if __name__ == "__main__":
	import subprocess
	subprocess.check_call('start powershell', shell=True)