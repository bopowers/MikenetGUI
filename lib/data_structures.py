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
..................................................................
The data_structures module contains the objects that store all model data.

Important classes are:
    MikenetScript
    MikenetIterator
    MikenetRun
    MikenetPhase
    MikenetTrainingProfile
    MikenetTestSet
    MikenetParameter

Taken together, these objects are hierarchical and form a tree,
where the script is the root node.

The levels of the tree are as follows:
    script(root)
        ->iterator level 1(optional)
            ->iterator level 2(optional)
                ->run
                    ->phase
                        ->training_set
                            ->parameter(leaf)
        ->test set
'''
from PySide import QtGui,QtCore
import tabs
import dialogs
from custom_widgets import CustomPhaseItemWidget
from editor_windows import TrainingProfileEditor,TestProfileEditor
import gen_utils as guts
from run_compiler import compileRun
from copy import deepcopy
import os
import decimal

class MikenetDataObject(object):
    def __init__(self,parent):
        # tree variables
        self.parent = parent
        self.children = []

        # a dictionary for this object's parameters
        self.parameters = {}

        # a tab widget (if applicable)
        self.tab_widget = None

        # a pointer to the main gui widget, for syncing data with tabs
        self.gui = None

    def createNew(self):
        # to be overriden by subclasses
        pass

    def getChildren(self):
        return self.children

    def removeChild(self,x):
        if x in self.children:
            self.children.remove(x)

    def getValueOf(self,p):
        return self.parameters[p].getValue()

    def getParameter(self,p):
        return self.parameters[p]

    def getTabWidget(self):
        return self.tab_widget

    def getClassName(self):
        return self.__class__.__name__

    def getGUI(self):
        return self.gui
        

class MikenetParameter():
    '''Doc here'''
    def __init__(self,gui,**kargs):
        # REQUIRED
        self.gui = gui
        # variable name is exactly as Mikenet will expect it
        self.variable_name = kargs['variable_name']
        
        # widget types: int_spinbox, dbl_spinbox, text_field,
        #               checkbox, dropdown, path
        self.widget_type = kargs['widget_type']

        if 'value' in kargs:
            if self.widget_type == 'text_field':
                # for text, need to cast as string
                self.value = str(kargs['value'])
            else:
                self.value = kargs['value']
        else:
            self.value = 0

        # recovery value to be used when a value needs to be undone
        # ie, when a user types an illegal value
        self.recovery_value = self.value

        if 'override_flag' in kargs:
            self.override_flag = kargs['override_flag']
        else:
            self.override_flag = 0

        if 'password_flag' in kargs:
            self.password_flag = kargs['password_flag']
        else:
            self.password_flag = 0

        # OPTIONAL
        # form name: if you want to display name differently in the GUI
        if 'form_name' in kargs:
            self.form_name = kargs['form_name']
        else:
            self.form_name = self.variable_name
        # comment: adds a comment to the form on the next row
        if 'comment' in kargs:
            self.comment = kargs['comment']
        else:
            self.comment = None
        # range, decimals, and step are optional for spinbox types
        if 'range' in kargs:
            self.minimum = kargs['range'][0]
            self.maximum = kargs['range'][1]
        else:
            self.minimum = self.maximum = None
        if 'step' in kargs:
            self.step = kargs['step']
        else:
            self.step = None
        if 'decimals' in kargs:
            self.decimals = kargs['decimals']
        else:
            self.decimals = None
        # categories are 'General','Timing','Output','Noise'
        if 'category' in kargs:
            self.category = kargs['category']
        else:
            self.category = None
        # dropdown_options: a list of option strings
        if 'dropdown_options' in kargs:
            self.dropdown_options = kargs['dropdown_options']
        else:
            self.dropdown_options = None
        # path object might have a label in another widget to update
        self.foreign_label = None # can be set later
        # path object needs to know an extension to look for
        if self.widget_type == 'path':
            if 'extension' in kargs:
                self.extension = kargs['extension']
            else:
                self.extension = '*.*' # default is all files
        else:
            self.extension = None

    def getWidget(self):
        '''Returns a widget that is connected to this parameter'''
        # save previous value
        self.recovery_value = self.value
        widget = None
        if self.widget_type == 'text_field':
            widget = QtGui.QLineEdit()
            widget.setText(self.value)
            if self.password_flag == 1:
                widget.setEchoMode(QtGui.QLineEdit.Password)
            widget.editingFinished.connect(lambda:
                                           self.setValue(widget.text()))
            
        elif 'spinbox' in self.widget_type:
            if self.widget_type == 'int_spinbox':
                widget = QtGui.QSpinBox()
            else:
                widget = QtGui.QDoubleSpinBox()
                if self.decimals:
                    widget.setDecimals(self.decimals)
            
            if self.minimum:
                widget.setMinimum(self.minimum)
            if self.maximum:
                widget.setMaximum(self.maximum)
            if self.step:
                widget.setSingleStep(self.step)
            
            widget.setValue(self.value)
            widget.valueChanged.connect(lambda:
                                        self.setValue(widget.value()))

        elif self.widget_type == 'checkbox':
            widget = QtGui.QCheckBox()
            if self.value == 1:
                widget.setCheckState(QtCore.Qt.Checked)
            else:
                widget.setCheckState(QtCore.Qt.Unchecked)
            widget.stateChanged.connect(lambda x:
                                        self.setValue(x/2))
                            
        elif self.widget_type == 'dropdown':
            widget = QtGui.QComboBox()
            if self.dropdown_options:
                for option in self.dropdown_options:
                    widget.addItem(option)
            widget.currentIndexChanged.connect(lambda x:
                                        self.setValue(x))

            widget.setCurrentIndex(self.value)

        elif self.widget_type == 'path':
            widget = QtGui.QLabel()
            if self.value:
                widget.setText(str(self.value))
            button = QtGui.QPushButton(self.form_name)
            button.clicked.connect(self.setPath)
            self.setForeignLabel(widget)
            return button,widget

        return self.form_name,widget         

    def setValue(self,value):
        #print 'value changed',value
        self.value = value

    def recover(self):
        self.value = self.recovery_value

    def getValue(self):
        return self.value

    def setPath(self):
        # a special case require selecting FOLDER,
        # and not FILE path. this is 'mikenet_path'
        if self.variable_name in ['mikenet_path']:
            fullpath = dialogs.specifyFolder(self.gui)
        else:
            fullpath = dialogs.specifyPath(self.gui,self.extension)
        if fullpath:
            self.setValue(fullpath)
            if self.foreign_label:
                self.foreign_label.setText(fullpath)

    def setForeignLabel(self,qlabel):
        '''For paths; allows any QLabel to be updated with changed path name'''
        self.foreign_label = qlabel
        
    def getCopy(self):
        '''Constructs a duplicate of this parameter.'''
        pDict = {'variable_name': self.variable_name,
                 'widget_type': self.widget_type,
                 'form_name': self.form_name}
        if self.override_flag == 1:
            pDict['override_flag'] = 1
        if self.password_flag == 1:
            pDict['password_flag'] = 1
        if self.comment:
            pDict['comment'] = self.comment
        if self.minimum:
            pDict['range'] = [self.minimum,self.maximum]
        if self.category:
            pDict['category'] = self.category
        if self.decimals:
            pDict['decimals'] = self.decimals
        if self.step:
            pDict['step'] = self.step
        if self.dropdown_options:
            # use deepcopy when copying compound objects like lists
            pDict['dropdown_options'] = deepcopy(self.dropdown_options)
        if self.extension:
            pDict['extension'] = self.extension
        
        # finally, write value last, because properties above need to be set first
        # (for spinboxs especially)
        pDict['value'] = self.value
            
        return MikenetParameter(self.gui,**pDict)
        
            
class MikenetPhaseItem(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetPhaseItem,self).__init__(parent)
        self.gui = gui

        # member variables
        self.my_profile = 'None'
        self.mode = 'TRAIN'
        self.overrides = []
        self.test_profiles = []
        self.recording_data = {}
        self.noise_data = {'weight_noise': {}, 'activation_noise': {}, 'input_noise': {}}
        self.net_components = {'groups': [],'connections': []}

        # null initialize parameters
        self.parameters = {'item_name': None,
                           'probability': None}

    def createNew(self):
        # name
        paramDict = {'variable_name': 'item_name',
                     'widget_type': 'text_field',
                     'form_name': 'Event Name',
                     'value': 'newEvent'}
        self.parameters['item_name'] = MikenetParameter(self.gui,**paramDict)
        # probability
        paramDict = {'variable_name': 'probability',
                     'widget_type': 'dbl_spinbox',
                     'range': [0,1],
                     'step': 0.05,
                     'decimals': 2,
                     'form_name': 'Proportion',
                     'comment': '(if phase order type is PROB)',
                     'value': 0.0}
        self.parameters['probability'] = MikenetParameter(self.gui,**paramDict)

        # register with the main gui so all tabs can be updated efficiently
        self.createTab()

    def createTab(self):
        self.tab_widget = tabs.PhaseItemTab(self)
        self.getGUI().registerTabbedObject(self)
        
    def getCopy(self):
        '''Constructs a duplicate of this node with the same data.
        
        The parent object of the copy is set to None and should be set manually by the 
        calling function as needed. Also the returned copy comes without any initialized 
        tab widget. This is because copying nodes for iteration purposes (when script
        is compiled) does not need a tab widget at all. 
        
        If you are duplicating from the GUI controls, then you need to manually add a tab 
        to this. The parent Phase has a tabifyChildren() function to add tabs to all its 
        children specifically for this purpose.
        '''
        pi_copy = MikenetPhaseItem(self.gui,None)
        # copy member variables
        pi_copy.my_profile = self.my_profile
        pi_copy.mode = self.mode
        # overrides are MikenetParameter objects, need to call their copy methods for each
        for p in self.overrides:
            pi_copy.overrides.append(p.getCopy())
        # use deepcopy when copying compound objects like lists
        pi_copy.test_profiles = deepcopy(self.test_profiles)
        pi_copy.recording_data = deepcopy(self.recording_data)
        pi_copy.noise_data = deepcopy(self.noise_data)     
        pi_copy.net_components = deepcopy(self.net_components)
        # finally copy phaseitem-level params
        for k,v in self.parameters.iteritems():
            pi_copy.parameters[k] = v.getCopy()
        return pi_copy

    def setProfile(self,prof):
        self.my_profile = prof

    def getProfile(self):
        return self.my_profile

    def getTestProfiles(self):
        return self.test_profiles

    def addTestProfile(self,profile):
        self.test_profiles.append(profile)

    def clearTestProfile(self,i):
        self.test_profiles.pop(i)
        
    def setRawRecordingData(self,data):
        self.recording_data = data
        
    def setRawNetComponents(self,data):
        self.net_components = data
        
    def setRawNoiseData(self,data):
        self.noise_data = data

    def setMode(self,train):
        if train:
            self.mode = 'TRAIN'
        else:
            self.mode = 'TEST'
            
    def setModeWithText(self,mode):
        self.mode = mode

    def getMode(self):
        return self.mode

    def newOverride(self,paramDict):
        self.overrides.append(MikenetParameter(self.gui,**paramDict))

    def getOverrides(self):
        return self.overrides

    def getGroupReadouts(self):
        '''Called at compile time.'''
        return sorted(self.recording_data.keys())

    def getAllRecordingTimes(self):
        '''Called at compile time.'''
        slices = []
        for key,values in self.recording_data.iteritems():
            # check to make sure this group was included
            if key in self.getComponentGroups():
                slices += values
        slices = list(set(slices))
        return slices

    def getSlicesByGroup(self):
        '''Called at compile time.'''
        num_ticks = self.parent.parent.getValueOf('ticks')
        slices = []
        for group in self.getGroupReadouts():
            if group in self.getComponentGroups():
                group_slice_data = []
                for t in range(num_ticks):
                    if t in self.recording_data[group]:
                        group_slice_data.append(1)
                    else:
                        group_slice_data.append(0)
                slices.append(group_slice_data)
        return slices
        
    def getPrintableParameters(self,prefix,suffix):
        # set decimal precision
        decimal.getcontext().prec = 4
        lines = []
        # get the profile
        profile = self.gui.getScript().getProfileByName(self.my_profile)
        for p in profile.getAllParameters():
            val = None
            # are we manually overriding this one?
            o = [x for x in self.overrides if x.variable_name == p.variable_name]
            if o:
                val = o[0].value
            else:
                val = p.value
            # also check for automatic overrides created by an iterator
            # these will take precedence over overrides at the phase-item level
            if p.form_name in self.parent.parent.getRunOverrides():
                # make sure the parameter is overriden on THIS event
                aps = self.parent.parent.override_paths[p.form_name]
                if aps == 'ALL':
                	val = self.parent.parent.getRunOverrides()[p.form_name]
                	print 'overriding',p.form_name,val
                else:
                    aps = [x for x in aps if (x.split(':')[0] == self.parent.getValueOf('phase_name'))\
                           and (x.split(':')[1] == self.getValueOf('item_name'))]
                    if aps:
                        val = self.parent.parent.getRunOverrides()[p.form_name]
                        print 'overriding',p.form_name,val
                
            if p.variable_name == 'profile_name':
                pass # skip this one
                
            elif p.variable_name == 'example_path':
                # only in TRAIN mode will a training set be used
                if self.mode == 'TRAIN':
                    if suffix == ';\n':
                        # writing to build_model.c
                        lines.append(prefix + 'train_examples=load_examples("' 
                                     + str(val) + '",TIME)' + suffix)
                    else:
                        # writing to metadata
                        h,t = os.path.split(val)
                        lines.append('train_examples=' + t + suffix)
            else:
                lines.append(prefix + p.variable_name + '=' + str(val) + suffix)
        return lines

    def swapRecordingEntry(self,old,new):
        if old in self.recording_data:
            self.recording_data[str(new)] = deepcopy(self.recording_data[str(old)])
            del self.recording_data[str(old)]
            
    def removeRecordingEntry(self,e):
        try:
            del self.recording_data[e]
        except:
            pass

    def getRecordingMatrix(self):
        num_ticks = self.parent.parent.getValueOf('ticks')
        matrix = []
        for group in sorted(self.getComponentGroups()):
            g_row = [0]*num_ticks
            if group in self.recording_data.keys():
                for j in range(num_ticks):
                    if j in self.recording_data[group]:
                        g_row[j] = 1
            matrix.append(g_row)
            
        return matrix
                        
    def toggleRecord(self,g,t):
        sorted_groups = sorted(self.getComponentGroups())
        g_name = sorted_groups[g]
        if g_name not in self.recording_data.keys():
            self.recording_data[g_name] = []

        if t in self.recording_data[g_name]:
            self.recording_data[g_name].remove(t)
            # is this group's entry empty now? if yes, delete it
            if not self.recording_data[g_name]:
                del self.recording_data[g_name]
        else:
            self.recording_data[g_name].append(t)

    def getComponentGroups(self):
        return  self.net_components['groups']
        
    def removeGroupComponent(self,c):
        try:
            self.net_components['groups'].remove(c)
        except:
            pass
            
    def removeConnectionComponent(self,c):
        try:
            self.net_components['connections'].remove(c)
        except:
            pass

    def getComponentConnections(self):
        return  self.net_components['connections']
        
    def getComponentMatrix(self):
        matrix = deepcopy(self.parent.parent.getMatrix())
        matrix = matrix[:-1] # ignore bias
        for connection in self.net_components['connections']:
            # connections are stored as informative strings
            # special character % splits these strings into the two groups
            g_from,g_to = connection.split('%')
            datafrom = [i for (i,x) in enumerate(self.parent.parent.getGroups())
                    if x['name'] == g_from]
            if datafrom:
                g_from = datafrom[0]
                datato = [i for (i,x) in enumerate(self.parent.parent.getGroups())
                    if x['name'] == g_to]
                if datato:
                    g_to = datato[0]
                    if matrix[g_from][g_to] > 0:
                        matrix[g_from][g_to] = 2
                
        return matrix
                        
    def toggleComponentGroup(self,g):
        group = self.parent.parent.getGroups()[g]
        if group['name'] in self.net_components['groups']:
            self.net_components['groups'].remove(group['name'])
        else:
            self.net_components['groups'].append(group['name'])

    def toggleComponentConnection(self,i,j):
        g_from = self.parent.parent.getGroups()[i]
        g_to = self.parent.parent.getGroups()[j]
        conn = g_from['name'] + '%' + g_to['name']
        if conn in self.net_components['connections']:
            self.net_components['connections'].remove(conn)
        else:
            self.net_components['connections'].append(conn)
            
    def getWeightNoiseData(self):
        return self.noise_data['weight_noise']
    
    def getActivationNoiseData(self):
        return self.noise_data['activation_noise']
    
    def getInputNoiseData(self):
        return self.noise_data['input_noise']

    def setWeightNoiseType(self,conn,i):
        # does entry already exist? preserve old value if it does
        # note: weight data is a list of the form [noise_type,value]
        if conn in self.noise_data['weight_noise']:
            old_val = self.noise_data['weight_noise'][conn][1]
        else:
            old_val = 0.0
        # now store the new noise type with the old (or default 0) value
        self.noise_data['weight_noise'][conn] = [i,old_val]
        
    def setWeightNoiseValue(self,conn,val):
        # does entry already exist? preserve old type if it does
        # note: weight data is a list of the form [noise_type,value]
        if conn in self.noise_data['weight_noise']:
            old_type = self.noise_data['weight_noise'][conn][0]
        else:
            old_type = 0
        # now store the new noise value with the old type
        self.noise_data['weight_noise'][conn] = [old_type,val]
        
    def setActivationNoiseValue(self,g,val):
        self.noise_data['activation_noise'][g] = val
        
    def setInputNoiseValue(self,g,val):
        self.noise_data['input_noise'][g] = val
        
    def removeNoiseRecord(self,noise_type,conn):
        del self.noise_data[noise_type][conn]

class MikenetPhase(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetPhase,self).__init__(parent)
        self.gui = gui
        
        # no other member variables, children are Phase Items
        
        # null-initialize parameters
        self.parameters = {'phase_name': None,
                           'phase_order': None,
                           'max_iterations': None}

        # no tab -- phase manipulation gets a special widget, shown in tabs.RunTab
        # that widget is created here
        self.widget = None

    def createNew(self):
        '''Sets default parameters for newly created data object.

        '''
        # create phase name parameter/widget
        paramDict = {'variable_name': 'phase_name',
                     'widget_type': 'text_field',
                     'form_name': 'Phase name',
                     'value': 'defaultPhase'}
        self.parameters['phase_name'] = MikenetParameter(self.gui,
                                                         **paramDict)

        # create phase order parameter/widget
        paramDict = {'variable_name': 'phase_order',
                     'widget_type': 'dropdown',
                     'form_name': 'Phase order',
                     'dropdown_options': ['SEQ','PROB'],
                     'value': 0}
        self.parameters['phase_order'] = MikenetParameter(self.gui,
                                                          **paramDict)

        # max iterations
        paramDict = {'variable_name': 'max_iterations',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000000],
                     'step': 100,
                     'form_name': 'Max iterations',
                     'value': 1000}
        self.parameters['max_iterations'] = MikenetParameter(self.gui,
                                                             **paramDict)

        
        self.createWidget()
        
    def getCopy(self):
        '''Constructs a duplicate of this node with the same data.
        
        The parent object of the copy is set to None and should be set manually by the 
        calling function as needed. Also the returned copy comes without any initialized 
        widget. This is because copying nodes for iteration purposes (when script
        is compiled) does not need a display widget at all. 
        
        If you are duplicating from the GUI controls, then you need to manually add a
        widget to this. The parent Run has a tabifyAll() function to add tabs to all its 
        children specifically for this purpose.
        '''
        phase_copy = MikenetPhase(self.gui,None)
        # copy phase parameters
        for k,v in self.parameters.iteritems():
            phase_copy.parameters[k] = v.getCopy()
        # copy phase items
        for pi in self.getChildren():
            pi_copy = pi.getCopy()
            pi_copy.parent = phase_copy # manually link phase copy with phase item copies
            phase_copy.children.append(pi_copy) # ...
        return phase_copy
            
    def tabifyChildren(self):
        for pi in self.getChildren():
            pi.createTab()

    def createWidget(self):
        self.widget = CustomPhaseItemWidget(self.parent.getTabWidget(),
                                               self)
        self.widget.hide()
        self.parent.getTabWidget().registerPhaseWidget(self.widget)
        self.parent.getTabWidget().refreshTabContents()

    def getWidget(self):
        return self.widget

    def destroyWidget(self):
        # unregister tabs in the main GUI for all children
        guts.DFS_deTab(self)
        self.widget.close()
        del self.widget

    def updateWidget(self):
        self.widget.syncToPhase()

    def hideWidget(self):
        self.widget.hide()
        
    def showWidget(self):
        self.widget.show()
        
    def newPhaseItem(self):
        item = MikenetPhaseItem(self.gui,self)
        item.createNew()
        self.children.append(item)
        self.widget.syncToPhase()

    def addTestRoutine(self,i):
        self.children.append(self.gui.script.getTestRoutines()[i])


def defaultGroup(name):
    g = {}
    g['name'] = name
    g['units'] = 10
    g['activation_type'] = 'LOGISTIC_ACTIVATION'
    g['error_computation_type'] = 'SUM_SQUARED_ERROR'
    return g


class MikenetRun(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetRun,self).__init__(parent)
        self.gui = gui
        
        # special member variables
        self.adjacency_matrix = [[]]
        self.groups = []
        self.run_overrides = {}
        self.override_paths = {} # extension of run_overrides, keeps track of events
        # note: run_overrides are only used when compiling a script...
        # they do not need to be saved or loaded from a file
        
        # null-initialize parameters
        self.parameters = {'run_name': None,
                           'seed': None,
                           'weight_range': None,
                           'bias_value': None,
                           'ticks': None}

    def createTab(self):
        self.tab_widget = tabs.RunTab(self)
        self.getGUI().registerTabbedObject(self)
        
    def createNew(self):
        '''Sets default parameters for newly created data object.'''
        self.newGroup('newGroup1')
        self.newGroup('newGroup2')
        
        # create run name parameter/widget
        # first, how many runs are there? we're going to use the
        # convention newRun1, newRun2, ... to avoid confusion for the user
        
        # simplest way to get all run names in the script is to iterate over the
        # lines in the script timeline. there is a method specifically for this
        # in the custom tree view widget
        existing = self.gui.getScript().getTabWidget().getNewRunNames()
        name_to_use = guts.getUnusedName('newRun',existing)
        
        paramDict = {'variable_name': 'run_name',
                     'widget_type': 'text_field',
                     'form_name': 'Run name',
                     'value': name_to_use}
        self.parameters['run_name'] = MikenetParameter(self.gui,
                                                       **paramDict)

        # create time ticks parameter/widget
        d = [x for x in self.gui.getScript().getDefaults()
            if x['variable_name'] == 'ticks']
        if d:
            paramDict = d[0]
        else:
            paramDict = {'variable_name': 'ticks',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Time ticks',
                     'value': 3}
        self.parameters['ticks'] = MikenetParameter(self.gui,
                                                    **paramDict)

        # create seed parameter/widget
        d = [x for x in self.gui.getScript().getDefaults()
            if x['variable_name'] == 'seed']
        if d:
            paramDict = d[0]
        else:
            paramDict = {'variable_name': 'seed',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Random seed',
                     'range': [0,999999999],
                     'step': 1,
                     'value': 1}
        self.parameters['seed'] = MikenetParameter(self.gui,
                                                    **paramDict)
        
        # create weight range parameter/widget
        d = [x for x in self.gui.getScript().getDefaults()
            if x['variable_name'] == 'weight_range']
        if d:
            paramDict = d[0]
        else:
            paramDict = {'variable_name': 'weight_range',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Weight range',
                     'range': [0,10],
                     'step': 0.01,
                     'value': 0.1} 
        self.parameters['weight_range'] = MikenetParameter(self.gui,
                                                           **paramDict)
        
        # create bias value parameter/widget
        d = [x for x in self.gui.getScript().getDefaults()
            if x['variable_name'] == 'bias_value']
        if d:
            paramDict = d[0]
        else:
            paramDict = {'variable_name': 'bias_value',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Bias value',
                     'range': [-10,10],
                     'step': 0.01,
                     'value': 1.0}
        self.parameters['bias_value'] = MikenetParameter(self.gui,
                                                         **paramDict)

        # make a new tab
        self.createTab()

        # make a default phase
        self.newPhase()
        
    def getCopy(self):
        '''Constructs a duplicate of this node with the same data.
        
        The parent object of the copy is set to None and should be set manually by the 
        calling function as needed. Also the returned copy comes without any initialized 
        tab widget. This is because copying nodes for iteration purposes (when script
        is compiled) does not need a tab widget at all. 
        
        If you are duplicating from the GUI controls, then you need to manually add a tab 
        to this and then to all children. The run has a tabifyChildren() function 
        specifically for this purpose.
        '''
        run_copy = MikenetRun(self.gui,None)
        # copy groups and connections
        # use deepcopy when copying compound objects like lists
        run_copy.setMatrix(deepcopy(self.getMatrix()))
        run_copy.setGroups(deepcopy(self.getGroups()))
        
        # Note: don't worry about copying run overrides...we want those to be
        # clear anyway if we are copying a run for iterating purposes in a script!
        
        # copy run-level parameters
        for k,v in self.parameters.iteritems():
            run_copy.parameters[k] = v.getCopy()
        # finally, copy phases
        for phase in self.getChildren():
            ph_copy = phase.getCopy()
            ph_copy.parent = run_copy # manually link run copy with phase copies
            run_copy.children.append(ph_copy) # ...
        return run_copy
        
    def tabifyChildren(self):
        for phase in self.children:
            phase.createWidget() # WARNING, parent tab widget must already exist!
            phase.tabifyChildren()

    def newPhase(self):
        phase = MikenetPhase(self.gui,self)
        phase.createNew()
        self.children.append(phase)

    def insertPhase(self,index,phase):
        self.children.insert(index,phase)

    def deletePhase(self,index):
        self.children[index].destroyWidget()
        ph = self.children.pop(index)
        # remove all phase references in any parent iterators
        traceNode = self.parent
        while True:
            if traceNode.getClassName() == 'MikenetIterator':
                if traceNode.getAppliedPaths() != 'ALL':
                    newPaths = [x for x in traceNode.getAppliedPaths() 
                               if x.split(':')[0] != ph.getValueOf('phase_name')]
                    traceNode.setAppliedPaths(newPaths)
                traceNode = traceNode.parent  
            else:
               break

    def getGroups(self):
        return self.groups

    def setGroups(self,g):
        self.groups = g

    def newGroup(self,name):
        self.addGroup(defaultGroup(name))

    def addGroup(self,g):
        self.groups.append(g)
        for row in self.adjacency_matrix[:-1]:
            row.append(0)
        # default is to add bias to this group
        self.adjacency_matrix[-1].append(1)

        new_matrix_row = [0]*len(self.groups)
        self.adjacency_matrix.insert(len(self.adjacency_matrix)-1,
                                     new_matrix_row)

    def deleteGroup(self,i):
        self.groups.pop(i)
        self.adjacency_matrix.pop(i)
        for x in self.adjacency_matrix:
            x.pop(i)
        self.gui.updateAllTabs()
            
        
    def renameGroup(self,index,name):
        self.groups[index]['name'] = name

    def getMatrix(self):
        return self.adjacency_matrix

    def setMatrix(self,a):
        self.adjacency_matrix = a

    def setConnection(self,i,j,value):
        self.adjacency_matrix[i][j] = value
        # on deletion, need to manually remove connections from children's components
        if value == 0 and i < len(self.groups):
            c = self.groups[i]['name'] + '%' + self.groups[j]['name']
            for ph in self.getChildren():
                for pi in ph.getChildren():
                    pi.getComponentConnections().remove(c)

    def overrideParameter(self,param_name,v,applied_paths):
        self.run_overrides[param_name] = v
        self.override_paths[param_name] = applied_paths

    def clearRunOverrides(self):
        self.run_overrides = {}
        self.override_paths = {}

    def getRunOverrides(self):
        return self.run_overrides

    def getOverridableParameters(self):
        '''Returns a list to the iterator of all params that can be overriden.'''
        op = []
        for phase in self.children:
            for pi in phase.getChildren():
                # add all parameters in the training set
                prof = self.getGUI().getScript().getProfileByName(pi.getProfile())
                if prof:
                    newps = [x.getCopy() for x in prof.getAllParameters() if
                             x.variable_name not in [y.variable_name for
                                                     y in op]]
                    op += newps
                # add noise params...we need to create parameters to hold them
                # activation and input noise
                for g in pi.getComponentGroups():
                    pDict = {'variable_name': 'activation_noise',
                            'widget_type': 'dbl_spinbox',
                            'range': [0,10],
                            'step': 0.001,
                            'decimals': 6,
                            'override_flag': 1,
                            'form_name': 'Activation noise on ' + str(g)}
                    op.append(MikenetParameter(self.gui, **pDict))
                    
                    pDict = {'variable_name': 'input_noise',
                            'widget_type': 'dbl_spinbox',
                            'range': [0,10],
                            'step': 0.001,
                            'decimals': 6,
                            'override_flag': 1,
                            'form_name': 'Input noise on ' + str(g)}
                    op.append(MikenetParameter(self.gui, **pDict))
                    
                # weight noise
                for c in pi.getComponentConnections():
                    pDict = {'variable_name': 'weight_noise',
                            'widget_type': 'dbl_spinbox',
                            'range': [0,10],
                            'step': 0.001,
                            'decimals': 6,
                            'override_flag': 1,
                            'form_name': 'Weight noise (additive) on ' + str(c.replace('%','->'))}
                    op.append(MikenetParameter(self.gui, **pDict))
                    
                for c in pi.getComponentConnections():
                    pDict = {'variable_name': 'weight_noise',
                            'widget_type': 'dbl_spinbox',
                            'range': [0,10],
                            'step': 0.001,
                            'decimals': 6,
                            'override_flag': 1,
                            'form_name': 'Weight noise (multiplicative) on ' + str(c.replace('%','->'))}
                    op.append(MikenetParameter(self.gui, **pDict))
                
        op = [x for x in op if x.override_flag == 1]
        # add run level parameters: seed, bias val, and weight range
        op.append(self.getParameter('seed').getCopy())
        op.append(self.getParameter('bias_value').getCopy())
        op.append(self.getParameter('weight_range').getCopy())
        return op
            
    def getDisplayLines(self):
        display_lines = ['<Run>','',
            str('Name: '+str(self.parameters['run_name'].getValue())),
            str('Seed: '+str(self.parameters['seed'].getValue()))]
        
        display_lines.append('Phases:')
        for phase in self.children:
            oi = phase.getValueOf('phase_order')
            order = phase.getParameter('phase_order').dropdown_options[oi]
            display_lines.append('    '+phase.getValueOf('phase_name')+' ('+order+')')
        display_lines.append('')
        display_lines.append('Train/test events:')
        for phase in self.children:
            for phase_item in phase.getChildren():
                display_lines.append('    '+phase_item.getValueOf('item_name'))
        display_lines.append('')
        display_lines.append('</Run>')
        
        return display_lines

class MikenetIterator(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetIterator,self).__init__(parent)
        self.gui = gui
        
        # special member variables
        self.my_run = None
        self.overridable_parameters = []
        self.random_flag = None
        self.varying_parameter = None
        self.applied_paths = 'ALL'
        
        # note: overridable parameters does not need to be saved or loaded
        # ...it is just a container that is filled when needed

        # null-initialize parameters
        self.parameters = {'iterator_name': None,
                           'varying': None,
                           'repeat': None,
                           'initial_value': None,
                           'delta': None}
        

    def createNew(self):
        '''Sets default parameters for newly created data object.

        '''
        # iterator name
        # simplest way to get all iterator names in the script is to iterate over the
        # lines in the script timeline. there is a method specifically for this
        # in the custom tree view widget
        existing = self.gui.getScript().getTabWidget().getIteratorNames()
        name_to_use = guts.getUnusedName('newIterator',existing)
        
        paramDict = {'variable_name': 'iterator_name',
                     'widget_type': 'text_field',
                     'form_name': 'Iterator name',
                     'value': name_to_use}
        self.parameters['iterator_name'] = MikenetParameter(self.gui,
                                                           **paramDict)
        # some filler values until the user specifies some
        paramDict = {'variable_name': 'varying',
                     'widget_type': 'dropdown',
                     'form_name': 'Parameter to vary',
                     'dropdown_options': [''],
                     'value': 0}
        self.parameters['varying'] = MikenetParameter(self.gui,
                                                           **paramDict)
        
        paramDict = {'variable_name': 'repeat',
                     'widget_type': 'int_spinbox',
                     'form_name': 'How many iterations?',
                     'range': [1,10000],
                     'step': 1,
                     'value': 1}
        self.parameters['repeat'] = MikenetParameter(self.gui,
                                                           **paramDict)
                                                           
        paramDict = {'variable_name': 'initial_value',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Initial value',
                     'range': [0,1000000],
                     'decimals': 3,
                     'step': 1}
        self.parameters['initial_value'] = MikenetParameter(self.gui,
                                                           **paramDict)
                                                           
        paramDict = {'variable_name': 'delta',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Change by how much each time?',
                     'range': [-1000000,1000000],
                     'decimals': 3,
                     'step': 1}
        self.parameters['delta'] = MikenetParameter(self.gui,
                                                           **paramDict)

        # make a new tab
        self.createTab()

    def getCopy(self):
        '''Constructs a duplicate of this node with the same data.
        
        The parent object of the copy is set to None and should be set manually by the 
        calling function as needed. Also the returned copy comes without any initialized 
        tab widget. This is because copying nodes for iteration purposes (when script
        is compiled) does not need a tab widget at all. 
        
        If you are duplicating from the GUI controls, then you need to manually add a tab 
        to this and then to all children. The iterator has a tabifyChildren() function 
        specifically for this purpose.
        '''
        iter_copy = MikenetIterator(self.gui,None)
        # copy iter-level parameters
        for k,v in self.parameters.iteritems():
            iter_copy.parameters[k] = v.getCopy()
        # finally, copy the child (should only be one child, either run or iterator)
        for child in self.getChildren():
            child_copy = child.getCopy()
            child_copy.parent = iter_copy # manually link child with iter_copy
            iter_copy.children.append(child_copy) # ...
            
        return iter_copy
        
    def tabifyChildren(self):
        for child in self.children:
            if child.getClassName() == 'MikenetRun':
                child.createTab()
            child.tabifyChildren()
            
    def getRandomFlag(self):
        return self.random_flag

    def setRandomFlag(self,rf):
        '''list of form: [type of random, min, max]'''
        self.random_flag = rf

    def getMyRun(self):
        return self.my_run

    def syncToRun(self):
        self.my_run = None
        # plumb the depths to find out if there is a run
        level = self
        while level.children:
            if level.children[0].getClassName() == 'MikenetRun':
                self.my_run = level.children[0]
                break
            else:
                level = level.children[0]
                
        self.updateVaryingMenu()
        if self.tab_widget:
            self.tab_widget.setRun(self.my_run)

    def setVarying(self,param):
        self.varying_parameter = param

    def updateVaryingMenu(self):
        # keep the old hidden units param if is was selected,
        # otherwise make a new one from scratch
        if self.varying_parameter and self.varying_parameter.variable_name == 'hidden_units':
            hu_param = self.varying_parameter
        else:
            pDict = {'variable_name': 'hidden_units',
                     'widget_type': 'text_field',
                     'form_name': 'Which group?',
                     'value': 'group_name',
                     'override_flag': 1}
            hu_param = MikenetParameter(self.getGUI(),**pDict)
 
        # fill the 'varying' menu box with parameters that can be overriden
        self.overridable_parameters = []
        if self.my_run:
            self.overridable_parameters += self.my_run.getOverridableParameters()
            
            # weed these out to get only spinbox values
            self.overridable_parameters = [x for x in self.overridable_parameters
                                           if 'spinbox' in x.widget_type]
            
            p_names = [''] + [x.form_name for x in self.overridable_parameters]

            # and add the hidden units param back
            self.overridable_parameters.append(hu_param)
            p_names.append('Number of hidden units')

            # finally, insert a null stub at the beginning
            self.overridable_parameters.insert(0,None)

            # make a new 'varying' box and populate with the options
            # if there is already a chosen parameter, set current index in box to it
            if self.varying_parameter:
                try:
                    # parameters might have changed, so encase in try/catch
                    if self.varying_parameter.variable_name == 'hidden_units':
                        new_val = len(self.overridable_parameters) - 1
                    else:
                        new_val = p_names.index(self.varying_parameter.form_name)
                except ValueError:
                    new_val = 0
            else:
                new_val = 0
            
            paramDict = {'variable_name': 'varying',
                 'widget_type': 'dropdown',
                 'form_name': 'Parameter to vary',
                 'dropdown_options': p_names,
                 'value': new_val}
        else:
            paramDict = {'variable_name': 'varying',
                 'widget_type': 'dropdown',
                 'form_name': 'Parameter to vary',
                 'dropdown_options': [''],
                 'value': 0}
        
        self.parameters['varying'] = MikenetParameter(self.gui,**paramDict)
        self.updateDependentFields(self.getValueOf('varying'))

    def updateDependentFields(self,i):
        if not i:
            self.setVarying(None)
            return
        if i > len(self.overridable_parameters) - 1:
            return
        # the ith parameter has been chosen from the varying menu
        self.setVarying(self.overridable_parameters[i])
        # update the other widgets accordingly
        if self.varying_parameter.widget_type in ['int_spinbox','text_field']:
            # make the new input widget take on all relevant properties
            self.parameters['initial_value'].widget_type = 'int_spinbox'
            self.parameters['delta'].widget_type = 'int_spinbox'
            if self.varying_parameter.minimum:
                self.parameters['initial_value'].minimum = self.varying_parameter.minimum
                self.parameters['initial_value'].maximum = self.varying_parameter.maximum
                self.parameters['delta'].minimum = self.varying_parameter.minimum
                self.parameters['delta'].maximum = self.varying_parameter.maximum
            if self.varying_parameter.step:
                self.parameters['initial_value'].step = self.varying_parameter.step
                self.parameters['delta'].step = self.varying_parameter.step
            try:
                self.parameters['initial_value'].value = int(self.parameters['initial_value'].value)
                self.parameters['delta'].value = int(self.parameters['delta'].value)
            except:
                self.parameters['initial_value'].value = 0
                self.parameters['delta'].value = 1
            
        elif self.varying_parameter.widget_type == 'dbl_spinbox':
            # make the new input widget take on all relevant properties
            self.parameters['initial_value'].widget_type = 'dbl_spinbox'
            self.parameters['delta'].widget_type = 'dbl_spinbox'
            if self.varying_parameter.minimum:
                self.parameters['initial_value'].minimum = self.varying_parameter.minimum
                self.parameters['initial_value'].maximum = self.varying_parameter.maximum
                self.parameters['delta'].minimum = self.varying_parameter.minimum
                self.parameters['delta'].maximum = self.varying_parameter.maximum
            if self.varying_parameter.step:
                self.parameters['initial_value'].step = self.varying_parameter.step
                self.parameters['delta'].step = self.varying_parameter.step
            if self.varying_parameter.decimals:
                self.parameters['initial_value'].decimals = self.varying_parameter.decimals
                self.parameters['delta'].decimals = self.varying_parameter.decimals
            try:
                self.parameters['initial_value'].value = float(self.parameters['initial_value'].value)
                self.parameters['delta'].value = float(self.parameters['delta'].value)
            except:
                self.parameters['initial_value'].value = 0.0
                self.parameters['delta'].value = 1.0

    def createTab(self):
        self.tab_widget = tabs.IteratorTab(self)
        self.getGUI().registerTabbedObject(self)
        
    def getAppliedPaths(self):
        return self.applied_paths
        
    def getPotentialPaths(self):
        potentials = []
        for ph in self.my_run.getChildren():
            for pi in ph.getChildren():
                potentials.append(str(ph.getValueOf('phase_name')+':'+pi.getValueOf('item_name')))
        return potentials
        
    def addAppliedPath(self,path):
        self.applied_paths.append(path)
        
    def removeAppliedPath(self,path):
        try:
            self.applied_paths.remove(path)
        except:
            pass
            
    def setAppliedPaths(self,ap):
        self.applied_paths = ap

    def getDisplayLines(self):
        time_txt = ''
        if self.getValueOf('repeat') > 1:
            time_txt = ' times'
        else:
            time_txt = ' time'
        if self.my_run:
            run_txt = self.my_run.getValueOf('run_name')
        else:
            run_txt = 'None'
        if self.varying_parameter:
            var_txt = self.varying_parameter.variable_name
        else:
            var_txt = 'None'
        display_lines = ['','Name: '+self.getValueOf('iterator_name'),
                         'Run: '+run_txt,
                         'Parameter: '+ var_txt,
                         'Repeat: '+str(self.getValueOf('repeat'))+time_txt,'']
        
        return display_lines

class MikenetTrainingProfile(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetTrainingProfile,self).__init__(parent)
        self.gui = gui
        
        # member variables
        self.category_labels = []

        # make parameters a list instead of a dict here to control order
        self.parameters = []

    def createNew(self):
        self.category_labels = ['General','Timing','Output']
        # first, how many training profiles are there? we're going to use
        # convention newTrainingProfile1, newTrainingProfile2, ...
        existing = [x.getValueOf('profile_name')
                    for x in self.parent.getChildren()
                    if 'TrainingSet' in x.getValueOf('profile_name')]
        name_to_use = guts.getUnusedName('TrainingSet',existing)
        
        # name
        paramDict = {'variable_name': 'profile_name',
                     'category': 'General',
                     'widget_type': 'text_field',
                     'form_name': 'Profile Name',
                     'value': name_to_use}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

        # example set
        paramDict = {'variable_name': 'example_path',
                     'category': 'General',
                     'widget_type': 'path',
                     'form_name': 'Example Set',
                     'override_flag': 1,
                     'value': 'None'}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

        # use defaults to fill in the rest of the parameters
        # look for the defaults with a 'category' defined and load them
        pDicts = [x for x in self.gui.getScript().getDefaults()
                  if 'category' in x]
        
        for p in pDicts:
            self.parameters.append(MikenetParameter(self.gui,**p))

    def getCopy(self):
        prof_copy = MikenetTrainingProfile(self.gui,None)
        for p in self.parameters:
            if p.variable_name == 'profile_name':
                # rename
                newName = p.getCopy()
                newName.value = (p.value + ' - COPY')
                prof_copy.parameters.append(newName)
            else:
                prof_copy.parameters.append(p.getCopy())
        # copy category labels
        prof_copy.setCategories(deepcopy(self.getCategories()))
        return prof_copy

    def getValueOf(self,parameter):
        param = [x for x in self.parameters if x.variable_name == parameter]
        if param:
            return param[0].value
        else:
            print 'Error: Not able to resolve parameter',parameter + '.'

    def getEditWindow(self):
        editor = TrainingProfileEditor(self,self.gui)
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def getCategories(self):
        return self.category_labels
        
    def setCategories(self,cats):
        self.category_labels = cats

    def getAllParameters(self):
        return self.parameters

    def getDisplayLines(self):
        ap = [x for x in self.parameters if x.variable_name == 'training_algorithm']
        alg = ap[0].dropdown_options[self.getValueOf('training_algorithm')]
        
        display_lines = ['<Training Set>','',
                         self.getValueOf('profile_name'),
                         str('Example Set: ' +
                             self.getValueOf('example_path')),
                         str('Algorithm: ' + alg),
                         str('Learning rate: ' +
                             str(self.getValueOf('epsilon'))),'',
                         '</Training Set>']
        return display_lines
        

class MikenetTestProfile(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent):
        # super constructor
        super(MikenetTestProfile,self).__init__(parent)
        self.gui = gui
        
        # member variables

        # make parameters a list instead of a dict here to control order
        self.parameters = []
        
    def createNew(self):
        # first, how many training profiles are there? we're going to use
        # convention newTrainingProfile1, newTrainingProfile2, ...
        existing = [x.getValueOf('profile_name')
                    for x in self.parent.getChildren()
                    if 'TestSet' in x.getValueOf('profile_name')]
        name_to_use = guts.getUnusedName('TestSet',existing)
        
        # name
        paramDict = {'variable_name': 'profile_name',
                     'widget_type': 'text_field',
                     'form_name': 'Profile Name',
                     'value': name_to_use}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

        # example set
        paramDict = {'variable_name': 'example_path',
                     'widget_type': 'path',
                     'form_name': 'Example Set',
                     'extension': '*.*',
                     'value': 'None'}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

        # path to .c file with myTestFunction()
        paramDict = {'variable_name': 'function_path',
                     'widget_type': 'path',
                     'form_name': 'Source file path',
                     'extension': '*.c',
                     'value': 'None'}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

        # additional args
        paramDict = {'variable_name': 'args',
                     'widget_type': 'text_field',
                     'form_name': 'Function args (optional)',
                     'value': ''}
        self.parameters.append(MikenetParameter(self.gui,**paramDict))

    def getCopy(self):
        prof_copy = MikenetTestProfile(self.gui,None)
        for p in self.parameters:
            if p.variable_name == 'profile_name':
                # rename
                newName = p.getCopy()
                newName.value = (p.value + ' - COPY')
                prof_copy.parameters.append(newName)
            else:
                prof_copy.parameters.append(p.getCopy())
        return prof_copy

    def getValueOf(self,parameter):
        param = [x for x in self.parameters if x.variable_name == parameter]
        if param:
            return param[0].value
        else:
            print 'Error: Not able to resolve parameter',parameter + '.'

    def getEditWindow(self):
        editor = TestProfileEditor(self,self.gui)
        editor.show()
        editor.raise_()
        editor.activateWindow()

    def getAllParameters(self):
        return self.parameters

    def getDisplayLines(self):
        display_lines = ['<Test Set>','',
                         self.getValueOf('profile_name'),
                         str('Example Set: ' +
                             self.getValueOf('example_path')),
                         str('Source File: ' +
                             self.getValueOf('function_path')),
                         str('Optional args: ' +
                             self.getValueOf('args')),'',
                         '</Test Set>']
        return display_lines


class MikenetProfileCollection(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui,parent,collection):
        # super constructor
        super(MikenetProfileCollection,self).__init__(parent)
        self.gui = gui
        self.children = collection
        

class MikenetScript(MikenetDataObject):
    '''Doc here'''
    def __init__(self,gui):
        # super constructor
        super(MikenetScript,self).__init__(None)
        self.gui = gui
        
        # special member variables
        self.defaults = []
        self.training_profiles = MikenetProfileCollection(gui,self,[])
        self.test_profiles = MikenetProfileCollection(gui,self,[])
        self.profiles_tab = None

        # null-initialize parameters
        self.parameters = {'script_name': None}

    def createTab(self):
        self.tab_widget = tabs.ScriptTab(self)
        self.profiles_tab = tabs.ProfilesTab(self)
        self.getGUI().registerTabbedObject(self)

    def createNew(self):
        '''Sets default parameters for newly created data object.

        '''
        # create script name parameter/widget
        paramDict = {'variable_name': 'script_name',
                     'widget_type': 'text_field',
                     'form_name': 'Script name',
                     'value': 'newScript'}
        self.parameters['script_name'] = MikenetParameter(self.gui,
                                                          **paramDict)

        # create default parameters ######################################
        # time
        self.defaults.append({'variable_name': 'ticks',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Time ticks',
                     'value': 3})

        # seed
        self.defaults.append({'variable_name': 'seed',
                     'widget_type': 'int_spinbox',
                     'form_name': 'Random seed',
                     'range': [0,999999999],
                     'step': 1,
                     'value': 1})
        
        # range
        self.defaults.append({'variable_name': 'weight_range',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Weight range',
                     'range': [0,10],
                     'step': 0.01,
                     'value': 0.1})
        
        # bias val
        self.defaults.append({'variable_name': 'bias_value',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Bias value',
                     'range': [-10,10],
                     'step': 0.01,
                     'value': 1.0})

        # epsilon
        self.defaults.append({'variable_name': 'epsilon',
                     'category': 'General',
                     'widget_type': 'dbl_spinbox',
                     'range': [0,10],
                     'step': 0.001,
                     'decimals': 3,
                     'form_name': 'Epsilon',
                     'override_flag': 1,
                     'value': 1.0})
        
        # momentum
        self.defaults.append({'variable_name': 'momentum',
                     'category': 'General',
                     'widget_type': 'dbl_spinbox',
                     'range': [0,1],
                     'step': 0.001,
                     'decimals': 3,
                     'form_name': 'Momentum',
                     'override_flag': 1,
                     'value': 0.0})
        
        # tolerance
        self.defaults.append({'variable_name': 'tolerance',
                     'category': 'General',
                     'widget_type': 'dbl_spinbox',
                     'range': [0,10],
                     'step': 0.001,
                     'decimals': 3,
                     'form_name': 'Tolerance',
                     'override_flag': 1,
                     'value': 0.1})

        # error radius
        self.defaults.append({'variable_name': 'error_radius',
                     'category': 'General',
                     'widget_type': 'dbl_spinbox',
                     'range': [0,10],
                     'step': 0.001,
                     'decimals': 3,
                     'form_name': 'Error radius',
                     'override_flag': 1,
                     'value': 0.0})
        
        # max iterations
        self.defaults.append({'variable_name': 'max_iterations',
                     'category': 'General',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000000],
                     'step': 100,
                     'form_name': 'Max iterations',
                     'override_flag': 1,
                     'value': 1000})
        
        # training mode
        self.defaults.append({'variable_name': 'training_mode',
                     'category': 'General',
                     'widget_type': 'dropdown',
                     'dropdown_options': ['BATCH','ONLINE'],
                     'form_name': 'Training mode',
                     'override_flag': 1,
                     'value': 0})

        # dbd
        self.defaults.append({'variable_name': 'dbd',
                     'category': 'General',
                     'widget_type': 'checkbox',
                     'form_name': 'Use dbd?',
                     'override_flag': 1,
                     'value': 0})
        
        # training algorithm
        self.defaults.append({'variable_name': 'training_algorithm',
                     'category': 'General',
                     'widget_type': 'dropdown',
                     'dropdown_options': ['BPTT','CRBP'],
                     'form_name': 'Algorithm',
                     'override_flag': 1,
                     'value': 0})
        
        # reset activation
        self.defaults.append({'variable_name': 'reset_activation',
                     'category': 'General',
                     'widget_type': 'checkbox',
                     'form_name': 'Reset activation each trial?',
                     'override_flag': 1,
                     'value': 1})
        
        # stop criterion
        self.defaults.append({'variable_name': 'stop_criterion',
                     'category': 'General',
                     'widget_type': 'dropdown',
                     'dropdown_options': ['MAX_ITER','MAX_ITER_OR_THRESH',
                                          'THRESHOLD'],
                     'form_name': 'Stop criterion',
                     'override_flag': 1,
                     'value': 0})

        # seconds
        self.defaults.append({'variable_name': 'seconds',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Seconds',
                     'range': [0,60],
                     'step': 0.1,
                     'decimals': 1,
                     'override_flag': 1,
                     'value': 1.0})
        
        # tai
        self.defaults.append({'variable_name': 'tai',
                     'category': 'Timing',
                     'widget_type': 'checkbox',
                     'form_name': 'Time average input?',
                     'override_flag': 1,
                     'value': 0})
        
        # error ramp
        self.defaults.append({'variable_name': 'error_ramp',
                     'category': 'Timing',
                     'widget_type': 'checkbox',
                     'form_name': 'Ramp error?',
                     'override_flag': 1,
                     'value': 0})
        
        # tao
        self.defaults.append({'variable_name': 'tao',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Time average output',
                     'range': [-1,1],
                     'decimals': 3,
                     'step': 0.001,
                     'override_flag': 1,
                     'value': 1.0})
        
        # tao max multiplier
        self.defaults.append({'variable_name': 'tao_max_mult',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Tao max multiplier',
                     'comment': '-1 means use 1/net->integrationConstant',
                     'range': [-1,1],
                     'decimals': 3,
                     'step': 0.001,
                     'override_flag': 1,
                     'value': -1.0})
        
        # tao min multiplier
        self.defaults.append({'variable_name': 'tao_min_mult',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Tao min multiplier',
                     'range': [-1,1],
                     'decimals': 3,
                     'step': 0.001,
                     'override_flag': 1,
                     'value': 0.001})
        
        # tao epsilon
        self.defaults.append({'variable_name': 'tao_epsilon',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Tao epsilon',
                     'range': [0,10],
                     'decimals': 3,
                     'step': 0.001,
                     'override_flag': 1,
                     'value': 0.0})
        
        # tao decay
        self.defaults.append({'variable_name': 'tao_decay',
                     'category': 'Timing',
                     'widget_type': 'dbl_spinbox',
                     'form_name': 'Tao decay',
                     'range': [0,10],
                     'decimals': 3,
                     'step': 0.001,
                     'override_flag': 1,
                     'value': 0.0})
        
        # will save weights
        self.defaults.append({'variable_name': 'will_save_weights',
                     'category': 'Output',
                     'widget_type': 'checkbox',
                     'form_name': 'Save weights?',
                     'override_flag': 1,
                     'value': 0})
        
        # save weights interval
        self.defaults.append({'variable_name': 'save_weights_interval',
                     'category': 'Output',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000],
                     'step': 100,
                     'form_name': 'Save weights interval',
                     'override_flag': 1,
                     'value': 500})
        
        # will save error
        self.defaults.append({'variable_name': 'will_save_error',
                     'category': 'Output',
                     'widget_type': 'checkbox',
                     'form_name': 'Save error log?',
                     'override_flag': 1,
                     'value': 1})
        
        # save error interval
        self.defaults.append({'variable_name': 'save_error_interval',
                     'category': 'Output',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000],
                     'step': 100,
                     'form_name': 'Save error interval',
                     'override_flag': 1,
                     'value': 500})

        # will save activations
        self.defaults.append({'variable_name': 'will_save_activations',
                     'category': 'Output',
                     'widget_type': 'checkbox',
                     'form_name': 'Save unit activations?',
                     'override_flag': 1,
                     'value': 0})
        
        # save activations interval
        self.defaults.append({'variable_name': 'save_activations_interval',
                     'category': 'Output',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000],
                     'step': 100,
                     'form_name': 'Save activations interval',
                     'override_flag': 1,
                     'value': 500})

        # test interval
        self.defaults.append({'variable_name': 'test_interval',
                     'category': 'Output',
                     'widget_type': 'int_spinbox',
                     'range': [1,1000000],
                     'step': 100,
                     'form_name': 'Test interval',
                     'override_flag': 1,
                     'value': 500})

        # make new tabs
        self.createTab()

    def getDefaults(self):
        return self.defaults

    def makeNewRun(self,parent):
        run = MikenetRun(self.gui,parent)
        run.createNew()
        return run

    def makeNewIterator(self,parent):
        it = MikenetIterator(self.gui,parent)
        it.createNew()
        return it

    def getProfileByName(self,name):
        # try training first
        profs = [x for x in self.training_profiles.getChildren()
                 if x.getValueOf('profile_name') == name]
        if profs:
            return profs[0]
        # then try test
        profs = [x for x in self.test_profiles.getChildren()
                 if x.getValueOf('profile_name') == name]
        if profs:
            return profs[0]

        # if no match found, return null
        return None


    def newTrainingProfile(self):
        prof = MikenetTrainingProfile(self.gui,self.training_profiles)
        prof.createNew()
        self.training_profiles.getChildren().append(prof)

    def newTestProfile(self):
        prof = MikenetTestProfile(self.gui,self.test_profiles)
        prof.createNew()
        self.test_profiles.getChildren().append(prof)
        
    def addTrainingProfile(self,profile):
        self.training_profiles.getChildren().append(profile)
        
    def addTestProfile(self,profile):
        self.test_profiles.getChildren().append(profile)

    def renameProfile(self,old_name,new_name):
        pass

    def removeTrainingProfile(self,profile):
        self.training_profiles.removeChild(profile)
        self.getGUI().updateAllTabs()

    def removeTestProfile(self,profile):
        self.test_profiles.removeChild(profile)
        self.getGUI().updateAllTabs()

    def getTrainingProfiles(self):
        return self.training_profiles
    
    def getTestProfiles(self):
        return self.test_profiles

    def getProfilesTabWidget(self):
        return self.profiles_tab



