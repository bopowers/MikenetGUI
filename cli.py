from PySide import QtGui,QtCore,QtSql
import argparse
from lib import io_utils as io
import sys
import os

class ScriptRunner():
    def __init__(self,args):
        self.showBriefLicense()
        self.parameters = {}
        self.script = None
        
        # get preferences
        self.loadPreferences()

        # load script from file
        self.script = io.cli_readScript(self,args.script)

        print self.script
        
        # scan script for errors
        #self.scanScript()
        
    def showBriefLicense(self):
        print '''
---------------------------------------------------------------------------
                                                     
MikeNetGUI Copyright (C) 2013-2014 Robert Powers

Developed at Haskins Laboratories, New Haven, CT.
(http://www.haskins.yale.edu/)

This program comes with ABSOLUTELY NO WARRANTY; for details see README file.
This is free software, and you are welcome to redistribute it
under certain conditions; see README file or click Help->About for details.

---------------------------------------------------------------------------

'''
        
    def loadPreferences(self):
        print 'Loading preferences...'
        try:
            with open(os.path.join(os.getcwd(),'resources','preferences'),'r') as f:
                lines = f.readlines()
                # preprocess by removing empty lines and stripping whitespace
                lines = [x.strip() for x in lines if x != '\n']
                i = 0
                while '</preferences>' not in lines[i]:
                    if '<parameter>' in lines[i]:
                        i = io.readParameter(lines,i+1,self,self)
                    i += 1
                
        except IOError:
            # try to reload the backup preferences
            print 'Encountered issues reading "resources/preferences"'
            print 'Attempting to restore backup preferences...'
            try:
                from shutil import copyfile
                copyfile(os.path.join(os.getcwd(),'resources','preferences_backup'),
                         os.path.join(os.getcwd(),'resources','preferences'))
                
                with open(os.path.join(os.getcwd(),'resources','preferences'),'r') as f:
                    lines = f.readlines()
                    # preprocess by removing empty lines and stripping whitespace
                    lines = [x.strip() for x in lines if x != '\n']
                    i = 0
                    while '</preferences>' not in lines[i]:
                        if '<parameter>' in lines[i]:
                            i = io.readParameter(lines,i+1,self,self)
                        i += 1
            except:
                print '''Error: There was a problem reading "resources/preferences". Quitting.'''

    def DFS_scan(self,node,issues):
        if node.getClassName() == 'MikenetScript':
            # check to make sure Mikenet is built and exists
            mknet_dir = self.parameters['mikenet_path'].value
            if not os.path.isdir(mknet_dir):
                issues.append('-ERROR: Mikenet directory does not exist. Try running resources/mikenet_installer.py.')
            if not os.path.isfile(os.path.join(mknet_dir,'lib','libmikenet.a')):
                issues.append('-ERROR: Mikenet does not appear to be built. Run resources/mikenet_installer.py to rebuild.')
        for child in node.getChildren():
            # go through the different cases
            if child.getClassName() == 'MikenetIterator':
                name = child.getValueOf('iterator_name')
                # does the iterator have a run?
                if not child.getMyRun():
                    issues.append('-ERROR: Iterator '+name+' has not been associated with a run object.')
                # does it have a valid parameter?
                if child.getParameter('varying').dropdown_options[child.getValueOf('varying')] in ['','None']:
                    issues.append('-ERROR: Iterator '+name+' does not seem to be defined on a valid parameter.')
                
            elif child.getClassName() == 'MikenetRun':
                name = child.getValueOf('run_name')
                # do any group names contain restricted characters?
                gnames = [x['name'] for x in child.getGroups()]
                y = [x for x in gnames if '%' in x]
                if y:
                    issues.append('-ERROR: At least one group in run '+name+' contains a restricted character ("%").')
                # are there any duplicate group names?
                if len(gnames) != len(set(gnames)):
                    issues.append('-ERROR: Run '+name+' contains duplicate group names. Group names must be unique.')
                
            elif child.getClassName() == 'MikenetPhase':
                name = child.getValueOf('phase_name')
                # if probabilistic, do phase items p values add up to 1?
                if child.getValueOf('phase_order') == 1:
                    pValues = [float(x.getValueOf('probability')) for x in child.getChildren()]
                    pSum = sum(pValues)
                    tol = 0.001
                    if pSum < (1 - tol) or pSum > (1 + tol):
                        issues.append('-ERROR: In run '+child.parent.getValueOf('run_name')+', phase '+name+
                                      ', p values need to add to 1 for probabilistic interleaving.')
                # is phase empty?
                if not child.getChildren():
                    issues.append('-ERROR: Run '+child.parent.getValueOf('run_name')+', phase '+name+
                                  ' has no training or test items defined.')
                
            elif child.getClassName() == 'MikenetPhaseItem':
                name = child.getValueOf('item_name')
                # are the network componenets empty?
                if len(child.net_components['groups']) == 0 and len(child.net_components['connections']) == 0:
                    issues.append('-ERROR: Phase item '+name+' includes no network components.')
                # check path only if this phase item overrides the training set path
                if 'example_path' in [x.variable_name for x in child.overrides]:
                    path = [x.value for x in child.overrides if x.variable_name == 'example_path']
                    if not os.path.isfile(path[0]):
                        # path does not exist
                        issues.append('-ERROR: Phase item '+name+' attempts to override example set with unresolvable path: '+
                                      str(path[0]))
                        issues.append('        ')
                    else:
                        # path exists, so scan file and attempt to find issues
                        issues += self.scanExamples(str('-In path override for item '+name+', '),path[0])
                
            # run one level deeper
            issues += self.DFS_scan(child,issues)
        return list(set(issues))

    def scanScript(self):
        pass

    def scanExamples(self,prefix,path):
        issues = []
        try:
            with open(path,'r') as f:
                lines = f.readlines()
                # remove empty lines, ; lines, TAG and PROB lines
                lines = [x for x in lines if x not in ['\n',';\n',';']]
                lines = [x for x in lines if x[:3] != 'TAG']
                lines = [x for x in lines if x[:4] != 'PROB']
                # now there should only be CLAMP and TARGET data lines
                # but not all lines will have 'CLAMP' or 'TARGET' explicitly, so
                # find those (calling them pivot lines here)
                pivots = [(i,x) for i,x in enumerate(lines)
                          if 'CLAMP' in x or 'TARGET' in x]
                # collect data about each clamp and each target
                fullclamp_data = {} # key-group, value-num_units
                fulltarget_data = {}

                for pindex,(i,pline) in enumerate(pivots):
                    split_line = pline.split()
                    # check line formatting
                    # each pivot line should have 'CLAMP/TARGET group_name time_data FULL/SPARSE'
                    if len(split_line) < 4:
                        issues.append(prefix+'line format error in example file: '+path)
                        # don't go any further
                        return issues
                    group = split_line[1]
                    # is time formatted correctly?
                    if split_line[2] != 'ALL':
                        try:
                            if type(int(split_line[2])) == int:
                                pass
                        except:
                            try:
                                l,r = split_line[2].split('-')
                                if type(int(l)) == int:
                                    pass
                                if type(int(r)) == int:
                                    pass
                            except:
                                issues.append(prefix+'incorrect time ticks format in example file: '+path)
                    # correctly uses FULL or SPARSE?
                    if split_line[3] not in ['FULL','SPARSE','FULL\n','SPARSE\n']:
                        issues.append(prefix+'line format error in example file: '+path)
                        # don't go any further
                        return issues
                    # now count units
                    if len(split_line) > 4:
                        # remainder contains any additional items in the pivot lines (units)
                        remainder = split_line[4:]
                        # don't count newline char
                        if remainder[-1] == '\n':
                            remainder = remainder[:-1]
                        ucount = len(remainder)
                    else:
                        ucount = 0

                    # do the units continue on the next line? count them if they do
                    i += 1
                    while i <= len(lines):
                        if i == len(lines):
                            break
                        elif (pindex+1) < len(pivots):
                            if i == pivots[pindex+1][0]:
                                break
                        next_split = lines[i].split()
                        if next_split[-1] == '\n':
                            next_split = next_split[:-1]
                        ucount += len(next_split)
                        i += 1
                        
                    if 'FULL' in split_line[3]:
                        if 'CLAMP' == split_line[0]:
                            # add the unit count for this group
                            if split_line[1] not in fullclamp_data:
                                fullclamp_data[split_line[1]] = []
                            fullclamp_data[split_line[1]].append(ucount)
                        elif 'TARGET' == split_line[0]:
                            # add the unit count for this group
                            if split_line[1] not in fulltarget_data:
                                fulltarget_data[split_line[1]] = []
                            fulltarget_data[split_line[1]].append(ucount)

                for k in fullclamp_data:
                    if len(set(fullclamp_data[k])) > 1:
                        issues.append(prefix+'unit mismatch for CLAMP FULL (group "'+str(k)+
                                      '": '+str(list(set(fullclamp_data[k])))+')')
                for k in fulltarget_data:
                    if len(set(fulltarget_data[k])) > 1:
                        issues.append(prefix+'unit mismatch for TARGET FULL (group "'+str(k)+
                                      '": '+str(list(set(fulltarget_data[k])))+')')
        except IOError:
            issues.append(prefix+'cannot open example path: '+path)
        return issues




def main():
    try: 
        app = QtGui.QApplication([])
            
    except RuntimeError:
        app = QtCore.QCoreApplication.instance()
        
    parser = argparse.ArgumentParser(description='Execute a MikeNet script file.')
    parser.add_argument('script',help='script name (plus extension if applicable) e.g. myScript.mnscript')
    #args = parser.parse_args(['blah']) ## commented on March 3 2015 to run from command line
    args = parser.parse_args()
    runner = ScriptRunner(args)

        
if __name__ == '__main__':
    main()
