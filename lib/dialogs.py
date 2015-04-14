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
from PySide import QtGui,QtCore
import sys,traceback
import os
from math import floor

def showWarning(parent,text):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('Warning')
    msgBox.setIcon(QtGui.QMessageBox.Warning)
    msgBox.setText(text)
    msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
    msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
    msgBox.exec_()


def showError(parent,inf_text,det_text):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('Error')
    msgBox.setIcon(QtGui.QMessageBox.Critical)
    msgBox.setText('An error has occurred.')
    msgBox.setInformativeText(inf_text)
    if det_text:
        msgBox.setDetailedText(det_text)
    msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
    msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
    msgBox.exec_()

def showInfo(parent,text):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('What is this?')
    msgBox.setIcon(QtGui.QMessageBox.Information)
    msgBox.setText(text)
    msgBox.setStandardButtons(QtGui.QMessageBox.Ok)
    msgBox.setDefaultButton(QtGui.QMessageBox.Ok)
    msgBox.exec_()   


def saveOnCloseDialog(parent):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('Save changes?')
    msgBox.setIcon(QtGui.QMessageBox.Question)
    msgBox.setText('Save script before closing?')
    msgBox.setStandardButtons(QtGui.QMessageBox.Save |
                              QtGui.QMessageBox.Discard |
                              QtGui.QMessageBox.Cancel)
    msgBox.setDefaultButton(QtGui.QMessageBox.Save)
    ret = msgBox.exec_()
    return ret

def saveOnNewDialog(parent):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('Save changes?')
    msgBox.setIcon(QtGui.QMessageBox.Question)
    msgBox.setText('Save current script first?')
    msgBox.setStandardButtons(QtGui.QMessageBox.Save |
                              QtGui.QMessageBox.Discard |
                              QtGui.QMessageBox.Cancel)
    msgBox.setDefaultButton(QtGui.QMessageBox.Save)
    ret = msgBox.exec_()
    return ret
        
def saveScript(parent):
    fname = None
    try:
        ftuple = QtGui.QFileDialog.getSaveFileName(parent, 'Save Script',
                                                   os.getcwd(),'*.mnscript')
        fname = str(ftuple[0])
    except:
        showError(parent,'Save was not successful from saveScript() method.',
                  traceback.print_exc())
    
    return fname

def specifyPath(parent,extension):
    fname = None
    try:
        fwindow = QtGui.QFileDialog(parent)
        fwindow.setFileMode(QtGui.QFileDialog.AnyFile)
        fwindow.setNameFilter(extension)
        fwindow.setDirectory(os.getcwd())
        fwindow.setConfirmOverwrite(False)
        fwindow.setWindowTitle('Specify Path')
        ret = fwindow.exec_()
        if ret == 1:
            ftuple = fwindow.selectedFiles()
            if ftuple:
                fname = str(ftuple[0])
            else:
                fname = None
        else:
            return None
    except:
        showError(parent,'Problem with path selection.',traceback.print_exc())
    
    return fname

def specifyFolder(parent):
    fname = None
    try:
        fwindow = QtGui.QFileDialog(parent)
        fwindow.setFileMode(QtGui.QFileDialog.Directory)
        fwindow.setOption(QtGui.QFileDialog.ShowDirsOnly)
        fwindow.setDirectory(os.getcwd())
        fwindow.setConfirmOverwrite(False)
        fwindow.setWindowTitle('Specify Directory')
        ret = fwindow.exec_()
        if ret == 1:
            ftuple = fwindow.selectedFiles()
            if ftuple:
                fname = str(ftuple[0])
            else:
                fname = None
        else:
            return None
    except:
        showError(parent,'Problem with path selection.',traceback.print_exc())
    
    return fname

def openScript(parent):
    fname = None
    try:
        ftuple = QtGui.QFileDialog.getOpenFileName(parent, 'Open Script', 
            os.getcwd(), 'MNScript Files (*.mnscript)')
        fname = str(ftuple[0])
    except:
        showError(parent,'Open was not successful from openScript() method.',
                  traceback.print_exc())

    return fname


def showAbout(parent):
    msgBox = QtGui.QMessageBox(parent)
    msgBox.setWindowTitle('About')
    icon = QtGui.QPixmap(os.path.join(os.getcwd(),'resources','images','about.png'))
    msgBox.setIconPixmap(icon)
    text = '''Copyright (C) 2013-2014 Robert Powers

Developed at Haskins Laboratories, New Haven, CT.
(http://www.haskins.yale.edu/)

MikeNetGUI is NOT MikeNet. MikeNet was developed by Michael W. Harm, and
is distributed freely under the GNU General Public License. Version 8.0
has been included with this package, and the original license information
can be viewed in the COPYING file within the Mikenet-v8.0 directory.

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
    msgBox.setText(text)
    
    msgBox.exec_()


class ScriptScreener(QtGui.QDialog):
    '''This dialog displays while scanning the script for errors.

    The algorithm is just a DFS search of the script tree which
    checks for common errors for each node type. Won't catch everything
    but may prevent a lot of bad runs, and will report what changes need
    to be made.'''
    def __init__(self,gui,issues):
        super(ScriptScreener, self).__init__(gui)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Script Check')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        redlight_layout = QtGui.QVBoxLayout()
        button_layout = QtGui.QHBoxLayout()

        # RED LIGHT (PROBLEM) WIDGETS
        redlight_layout.addWidget(QtGui.QLabel('The following script issues were identified:'))
        self.issue_list = QtGui.QListWidget()
        redlight_layout.addWidget(self.issue_list)
        for i in issues:
            self.issue_list.addItem(i)
        redlight_layout.addWidget(QtGui.QLabel('Address these issues first and try again.'))
            
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        button_layout.addWidget(self.ok_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(redlight_layout)
        main_layout.addLayout(button_layout)

    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().width('xxx'*30),
                            200)

    def okAction(self):
        self.accept()

class ScanningThread(QtCore.QThread):
    def __init__(self,script):
        super(ScanningThread,self).__init__(script.getGUI())
        self.script = script
        self.issues = []
        
    def run(self):
        self.DFS_scan(self.script,self.issues)
        # also check the training and test profiles
        for p in self.script.getTrainingProfiles().getChildren():
            path = p.getValueOf('example_path')
            self.issues += self.scanExamples(str('-In training set '+p.getValueOf('profile_name')+', '),path)
        for p in self.script.getTestProfiles().getChildren():
            path = p.getValueOf('example_path')
            self.issues += self.scanExamples(str('-In test set '+p.getValueOf('profile_name')+', '),path)
        self.issues = list(set(self.issues))

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

    def DFS_scan(self,node,issues):
        if node.getClassName() == 'MikenetScript':
            # check to make sure Mikenet is built and exists
            mknet_dir = node.getGUI().parameters['mikenet_path'].value
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
    

class ProgressWindow(QtGui.QDialog):
    def __init__(self,gui):
        super(ProgressWindow, self).__init__(gui)
        self.gui = gui
        self.num_runs = 0
        self.run_counter = 0
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Script Progress')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        h_layout = QtGui.QHBoxLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # STUFF
        self.cores = QtGui.QLabel('')
        self.progbar = QtGui.QProgressBar()
        self.progbar.setRange(0,0)
        self.eltime = QtGui.QLabel('')
        self.status = QtGui.QLabel('Preparing runs...')
            
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.hide()
        self.cancel_btn = QtGui.QPushButton('Abort')
        button_layout.addWidget(self.ok_btn)
        #button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(self.cores)
        main_layout.addWidget(self.progbar)
        main_layout.addWidget(self.eltime)
        main_layout.addWidget(self.status)
        main_layout.addLayout(button_layout)

    def sizeHint(self):
        return QtCore.QSize(1.5*self.fontMetrics().width('x'*50),
                            300)

    def simulationOver(self,run_time):
        if self.gui.parameters['use_database'].value == 1:
            # what is most natural way to state the time?
            hours = str(str(int(floor(run_time/3600))) + 'h')
            minutes = str(str(int(floor((run_time % 3600)/60))) + 'm')
            seconds = str(str(round((run_time % 3600) % 60)) + 's')
            self.eltime.setText('Final running time: '+': '.join([hours,minutes,seconds]))
        self.ok_btn.show()
        self.progbar.hide()
        #self.cancel_btn.hide()

    def updateCores(self,cores):
        if cores < 0:
            self.cores.setText('Multiprocessing disabled. Running in serial mode.')
        else:
            self.cores.setText(str('Utilizing ' + str(cores) + ' CPUs.'))

    def updateTotalProgress(self,complete,total,run_time):
        # what is most natural way to state the time?
        hours = str(str(int(floor(run_time/3600))) + 'h')
        minutes = str(str(int(floor((run_time % 3600)/60))) + 'm')
        seconds = str(str(round((run_time % 3600) % 60)) + 's')
        self.eltime.setText(': '.join([hours,minutes,seconds]))
        self.status.setText('In progress: '+str(complete)+'/'+str(total)+' runs completed...')

    def updateSuccessRatio(self,good,total):
        self.status.setText('Script complete with '+str(good)+'/'+str(total)+
                            ' runs successful.')

    def okAction(self):
        self.accept()

    def cancelAction(self):
        self.gui.getScript().getTabWidget().abortScript()


