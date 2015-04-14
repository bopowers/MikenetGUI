#!/usr/bin/env python
'''
Copyright (C) 2013-2014 Robert Powers

This file is part of MikeNetGUI.

MikeNetGUI is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

MikeNetGUI is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with MikeNetGUI.  If not, see <http://www.gnu.org/licenses/>.
'''
import os
import subprocess
import sys
import tarfile
from shutil import copyfile

def query_yes_no(question, default="yes"):
    """Ask a yes/no question via raw_input() and return their answer.

    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes" or "no".
    """
    valid = {"yes":True,   "y":True,  "ye":True,
             "no":False,     "n":False}
    if default == None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "\
                             "(or 'y' or 'n').\n")
def query_build_preference(question):
    """Same as query_yes_no, except values are "s","m"

    The "answer" return value is one of "s" or "m" (or None to cancel).
    """
    valid = {"scons":"s", "s":"s", "sc":"s", "sco":"s", "scon":"s",
             "make":"m", "m":"m", "ma":"m", "mak":"m",
             "cancel":None, "c":None, "ca":None, "can":None,
             "canc":None, "cance":None}
    
    prompt = " [scons/make/cancel] "

    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'scons', 'make', or 'cancel'"\
                             "(or 's', 'm', or 'c').\n")

def query_compiler(question):
    valid = {"0": "gcc", "1": "ansi", "2": "cc",
             "3": "linux", "4": "sparc", "5": "hp"}

    prompt = " [0=gcc, 1=ansi, 2=cc, 3=linux, 4=sparc, 5=hp] "
    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if choice in valid:
            return valid[choice]
        else:
            return valid["0"]


def build_with_scons():
    # write the following SConstruct file
    print "Writing SConstruct file in resources/Mikenet-v8.0/src"

    build_code = '''objects = []

objects += Object('example.c')
objects += Object('net.c')
objects += Object('tools.c')
objects += Object('crbp.c')
objects += Object('random.c')
objects += Object('token.c')
objects += Object('parallel.c')
objects += Object('bptt.c')
objects += Object('linesearch.c')
objects += Object('weights.c')
objects += Object('error.c')
objects += Object('stats.c')
objects += Object('apply.c')
objects += Object('analyze.c')
objects += Object('dbm.c')
objects += Object('elman.c')
objects += Object('benchmark.c')
objects += Object('dotprod.c')
objects += Object('matrix.c')
objects += Object('fastexp.c')

Library('libmikenet', objects)'''

    with open("SConstruct","w") as f:
        f.write(build_code)

    # call SCons to build libmikenet.a
    print "Building 'libmikenet.a' with SCons..."
    subprocess.call("scons -c",shell=True)
    subprocess.call("scons",shell=True)

    # check to make sure build was successful
    if not os.path.isfile("libmikenet.a"):
        print "Error - SCons library build was not successful."
        print "Check your SCons installation, and try again."
        print "Installation cancelled."
        sys.exit(0)
            
    print "SCons build successful..."

def build_with_make():
    # what is the compiler to use?
    compiler_pref = query_compiler("What compiler? (any key for gcc)")
    subprocess.call("make clean",shell=True)
    subprocess.call(str("make "+compiler_pref),shell=True)

    # check to make sure build was successful
    if not os.path.isfile("libmikenet.a"):
        print "Error - Library build using Make was not successful."
        print "Installation cancelled."
        sys.exit(0)

    print "Make build successful..."
    

print '''---------------------------------------------------------------------------
MikeNetGUI Copyright (C) 2013-2014 Robert Powers

Developed at Haskins Laboratories, New Haven, CT.
(http://www.haskins.yale.edu/)

This program comes with ABSOLUTELY NO WARRANTY; for details see README file.
This is free software, and you are welcome to redistribute it
under certain conditions; see README file or click Help->About for details.
---------------------------------------------------------------------------

Welcome to the MikeNetGUI "MikeNet Installer."

This will build a modified version of the Mikenet-v8.0 library.
to be used with MikeNetGUI.
'''
if not query_yes_no("Is this what you want to do?", None):
    print "Installation cancelled."
    sys.exit(0)

# first untar Mikenet distribution
if not os.path.isdir("Mikenet-v8.0"):
    if not os.path.isfile("mikenet_v8.tar.gz"):
        print "Error - Cannot locate mikenet_v8.tar.gz."
        print "Download it, put it in the resources directory and try again."
        print "Installation cancelled."
        sys.exit(0)
    print "Unpackaging archive 'mikenet_v8.tar.gz'..."
    tar = tarfile.open("mikenet_v8.tar.gz")
    tar.extractall()
    tar.close()

# cd into the Mikenet-v8.0 src directory
os.chdir(os.path.join("Mikenet-v8.0","src"))

# are we using SCons or Make?
# get the preference
usr_build_pref = query_build_preference("Choose your preferred build tool:")
if not usr_build_pref:
    print "Installation cancelled."
    sys.exit(0)
# search the system path for scons
print 'Searching for preferred build tool...'
path_str = os.getenv('PATH')
path_dirs = path_str.split(os.pathsep)
found_scons = False
found_make = False
    
for location in path_dirs:
    try:
        files = os.listdir(location)
        for f in files:
            if 'scons.exe' in f:
                found_scons = True
                break
            elif 'scons' == f: # unix
                found_scons = True
                break
            elif 'make' == f:
                found_make = True
            elif 'gmake' == f:
            	found_make = True
    except:
        pass
if usr_build_pref == 's':
    # SCons is preferred
    if found_scons:
        print 'SCons found on path, preparing to build...'
        build_with_scons()
    elif found_make:
        print 'SCons not found on path, using Make instead.'
        build_with_make()
    else:
        print 'Error - Cannot locate SCons or Make utilities.'
        print 'Make sure SCons (or Make) is on your system path  and try again.'
        print 'Installation cancelled.'
        sys.exit(0)
else:
    # Make is preferred
    if found_make:
        print 'Make found on path, setting up build...'
        build_with_make()
    elif found_scons:
        print 'Make not found on path, using SCons instead.'
        build_with_scons()
    else:
        print 'Error - Cannot locate Make or SCons utilities.'
        print 'Make sure SCons (or Make) is on your system path  and try again.'
        print 'Installation cancelled.'
        sys.exit(0)

# if it was successful, copy libmikenet.a to Mikenet-v8.0/lib
print "Copying 'libmikenet.a' to resources/Mikenet-v8.0/lib..."
copyfile("libmikenet.a",os.path.join("..","lib","libmikenet.a"))

# chdir back to the resources folder
os.chdir(os.pardir)
os.chdir(os.pardir)

# finally, set the MikeNet directory path in 'preferences' file
print "Updating MikenetGUI preferences file..."
with open("preferences","r") as f:
    lines = f.readlines()
    path_flag = False
    build_flag = False
    new_path_line = None
    new_path_index = 0
    new_build_line = None
    new_build_index = 0
    for i,line in enumerate(lines):
        if path_flag and "value =" in line:
            # original line looks like \t\tvalue = blahblah;
            # split on the equals sign
            l,r = line.split("=")
            new_path_line = str(l + "= " +
                        os.path.join(os.getcwd(),"Mikenet-v8.0") + ';\n')
            new_path_index = i
            path_flag = False

        elif build_flag and "value =" in line:
            # original line looks like \t\tvalue = blahblah;
            # split on the equals sign
            if found_scons:
                val = 0
            else:
                val = 1
            l,r = line.split("=")
            new_build_line = str(l + "= " + str(val) + ';\n')
            new_build_index = i
            build_flag = False
        
        elif "mikenet_path" in line:
            # prepare to find value in a couple of lines
            path_flag = True

        elif "build_method" in line:
            # prepare to find vlaue in a couple of lines
            build_flag = True
            
lines[new_path_index] = new_path_line
lines[new_build_index] = new_build_line

with open("preferences","w") as f:
    f.writelines(lines)

# NEVER write to the preferences backup file. leave it alone just in case
	
# finally, do the same thing in the template SConstruct and Make files
# SLIGHTLY different code than the preferences writing above
#
#SCons
with open(os.path.join("template_code","SConstruct"),"r") as f:
    lines = f.readlines()
    new_path_line = None
    new_path_index = 0
    for i,line in enumerate(lines):
        if "MIKENET_DIR =" in line:
            # original line looks like MIKENET_DIR = blahblah;
            # split on the equals sign
            new_path_str = os.path.join(os.getcwd(),"Mikenet-v8.0")
            if sys.platform == 'win32':
                new_path_str = new_path_str.replace('\\','/')

            l,r = line.split("=")
            new_path_line = str(l + "= os.path.normpath('" +
                         new_path_str + "')\n")
            new_path_index = i
            break
            
lines[new_path_index] = new_path_line

with open(os.path.join("template_code","SConstruct"),"w") as f:
    f.writelines(lines)
#Make
with open(os.path.join("template_code","Makefile"),"r") as f:
    lines = f.readlines()
    new_path_line = None
    new_path_index = 0
    for i,line in enumerate(lines):
        if "MIKENET_DIR=" in line:
            # original line looks like MIKENET_DIR=blahblah;
            # split on the equals sign
            l,r = line.split("=")
            new_path_line = str(l + "=" +
                        os.path.join(os.getcwd(),"Mikenet-v8.0") + "\n")
            new_path_index = i
            break
            
lines[new_path_index] = new_path_line

with open(os.path.join("template_code","Makefile"),"w") as f:
    f.writelines(lines)

# return to original home directory
os.chdir(os.pardir)

print "Installation complete. You may exit any time."
            
