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
from custom_widgets import CustomListWidget,CustomWiringWidget
from custom_widgets import CustomTreeWidget,CustomPhaseWidget
from custom_widgets import CustomRecordingWidget,CustomComponentSelectionWidget
from custom_widgets import CustomInteractiveParamWidget,CustomTestSetSelectionWidget
from custom_widgets import CustomWeightNoiseWidget,CustomActivationNoiseWidget
from custom_widgets import CustomInputNoiseWidget,CustomApplyIterationWidget
from editor_windows import DefaultsEditor
from multiproc import ScriptThread
import psutil
import sys
import pydot
# test pydot to find out if Graphviz is installed
if pydot.find_graphviz():
    pass
else:
    print 'Graphviz executables not found. "Visualize" feature will be disabled.'
from matplotlib import pyplot
from scipy import misc
import gen_utils as guts
import os
import dialogs
from time import time

class ScriptTab(QtGui.QWidget):
    '''Creates a tab with tools for script-level editing.

    The widget is arranged in two columns. Each column is arranged using
    a vertical layout.

    '''
    def __init__(self,script):
        super(ScriptTab, self).__init__()
        self.script = script
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        #..............................................................
        # LAYOUTS

        # create main horizontal layout
        h_layout = QtGui.QHBoxLayout()
        # left and right column layouts
        left_v_layout = QtGui.QVBoxLayout()
        right_v_layout = QtGui.QVBoxLayout()
        # sublayouts for timeline control, script property editing, start button
        time_layout = QtGui.QGridLayout()
        props_layout = QtGui.QFormLayout()
        start_layout = QtGui.QHBoxLayout()

        #..............................................................
        # HIERARCHICAL TREE VIEW OBJECT (ENTIRE LEFT COLUMN)
        # see custom_widgets module for CustomTreeWidget definitions
        self.tree_view = CustomTreeWidget(self,script)

        #..............................................................
        # TIMELINE EDITING CONTROLS (ADD RUN/ITERATION, REMOVE, ETC...)
        
        # create timeline editing buttons
        self.add_run_btn = QtGui.QPushButton('Add Run')
        self.add_iter_btn = QtGui.QPushButton('Add Iterator')
        self.del_btn = QtGui.QPushButton('Remove Selected')
        self.del_btn.setEnabled(False)
        self.dup_btn = QtGui.QPushButton('Duplicate Selected')
        self.dup_btn.setEnabled(False)

        # create timeline editing group box
        timeline_container = QtGui.QHBoxLayout() # to shift everything over
        timeline = QtGui.QGroupBox('Edit Script Timeline')
        timeline.setAlignment(QtCore.Qt.AlignHCenter)
        time_layout.setSpacing(10)
        time_layout.addWidget(self.add_run_btn,0,0,1,1)
        time_layout.addWidget(self.add_iter_btn,1,0,1,1)
        time_layout.addWidget(self.del_btn,0,1,1,1)
        time_layout.addWidget(self.dup_btn,1,1,1,1)
        timeline.setLayout(time_layout)
        timeline_container.addWidget(timeline)
        #timeline_container.addStretch(1)

        # connect button signals
        self.add_run_btn.clicked.connect(self.tree_view.newRun)
        self.add_iter_btn.clicked.connect(self.tree_view.newIterator)
        self.dup_btn.clicked.connect(self.tree_view.duplicateCurrentObject)
        self.del_btn.clicked.connect(self.tree_view.removeCurrentObject)

        #..............................................................
        # SCRIPT PROPERTIES BOX

        # create script properties panel
        props = QtGui.QGroupBox('Script Properties')
        props.setAlignment(QtCore.Qt.AlignHCenter)
        script_name,script_box = self.script.getParameter('script_name').getWidget()
        #defaults_btn = QtGui.QPushButton('Edit global parameter defaults')
        #defaults_btn.clicked.connect(self.editDefaults)
        props_layout.addRow(script_name,script_box)
        #props_layout.addRow('',defaults_btn)
        props.setLayout(props_layout)

        # connect signals
        script_box.editingFinished.connect(self.updateTabName)

        #..............................................................
        # START BUTTON
        self.start_btn = StartButton(self)
        self.start_btn.clicked.connect(self.scanScript)

        #..............................................................                 
        # putting it all together
        self.setLayout(h_layout)
        h_layout.addLayout(left_v_layout)
        left_v_layout.addWidget(QtGui.QLabel('Script Timeline'))
        left_v_layout.addWidget(self.tree_view)
        h_layout.addLayout(right_v_layout)
        right_v_layout.addLayout(timeline_container)
        right_v_layout.addWidget(props)
        right_v_layout.addLayout(start_layout)
        start_layout.addStretch(1)
        start_layout.addWidget(self.start_btn)
        start_layout.addStretch(1)
        right_v_layout.addStretch(1)
        
        # initialize
        self.tree_view.syncToModel()

    def scanScript(self):
        self.start_btn.setScanning()
        self.scan_thread = dialogs.ScanningThread(self.script)
        self.scan_thread.finished.connect(self.reportScriptIssues)
        self.scan_thread.start()
        
    def startScript(self):
        self.start_btn.setInProgress()
        # start script run
        self.prog = dialogs.ProgressWindow(self.script.getGUI())
        self.prog.show()
        self.prog.raise_()
        self.prog.activateWindow()
        
        self.script_thread = ScriptThread(self.script)
        self.script_thread.finished.connect(self.notifyScriptEnded)
        # time the entire script
        self.tic = time()
        self.script_thread.start()

    def abortScript(self):
        early_abort = True
        self.script_thread.quit()
        # kill all processes
        for proc in psutil.process_iter():
            if 'mikenet_master' in proc.name:
                proc.kill()
            #if 'mikenet_master' in proc.name():
            #   print 'killed a process'
            #   proc.kill()
            #try:
            #    print proc.name()
            #    if 'mikenet_master' in proc.name():
            #        proc.kill()
            #except:
            #    print 'excepted process search'
        
    @QtCore.Slot()
    def reportScriptIssues(self):
        if self.scan_thread.issues:
            screener = dialogs.ScriptScreener(self.script.getGUI(),
                                              self.scan_thread.issues)
            screener.exec_()
            self.start_btn.setFree()
        else:
            self.startScript()

    @QtCore.Slot(int)
    def updateCores(self,i):
        self.prog.updateCores(i)

    @QtCore.Slot(int,int)
    def updateTotalProgress(self,complete,total):
        toc = time()
        self.prog.updateTotalProgress(complete,total,toc-self.tic)
        
    @QtCore.Slot(int,int)
    def updateSuccessRatio(self,good,total):
        self.prog.updateSuccessRatio(good,total)        

    def notifyScriptEnded(self):
        # gets activated after script runs and database is finished updating
        toc = time()
        self.prog.simulationOver(toc-self.tic)
        self.script.getGUI().emailNotify(toc-self.tic)
        self.start_btn.setFree()

    def getNewRunNames(self):
        return self.tree_view.getNewRunNames()

    def getIteratorNames(self):
        return self.tree_view.getIteratorNames()

    def editDefaults(self):
        ed = DefaultsEditor(self.script.getGUI(),self.script)
        ed.exec_()

    def refreshTabContents(self):
        self.tree_view.syncToModel()

    def getTabName(self):
        return str('Script Object: ' + self.script.getValueOf('script_name'))

    def updateTabName(self):
        self.script.getGUI().getMainTabs().refreshTabNames()

    def getLevel(self):
        return 0

class StartButton(QtGui.QPushButton):
    def __init__(self,parent):
        super(StartButton, self).__init__('Start Script',parent=parent)
        self.setStyleSheet('background-color: green;' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')

        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Maximum)
        self.timer = QtCore.QTimer(self)
        self.timer.start(10)
        self.timer.timeout.connect(self.hover)

    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().width('xxxxxxxxxxxxxxxxxxxxx'),
                            3*self.fontMetrics().height())

    def hover(self):
        self.timer.start(10)
        if self.underMouse() == True:
            self.setStyleSheet('background-color: rgb(152,245,255);' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')
        else:
            self.setStyleSheet('background-color: green;' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')

    def setScanning(self):
        self.timer.stop()
        self.setStyleSheet('background-color: orange;' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')
        self.setText('Checking for errors...')
        self.setEnabled(False)
        self.repaint()

    def setInProgress(self):
        self.timer.stop()
        self.setStyleSheet('background-color: orange;' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')
        self.setText('In progress...')
        self.setEnabled(False)
        self.repaint()

    def setFree(self):
        self.timer.start(10)
        self.setStyleSheet('background-color: green;' +
                           'border-style: outset;' +
                           'border-width: 2px;' +
                           'border-radius: 10px;' +
                           'border-color: white;' +
                           'font: bold 14px;' +
                           'min-width: 10em;' +
                           'padding: 6px;')
        self.setText('Start Script')
        self.setEnabled(True)
        self.repaint()
            

class RunTab(QtGui.QWidget):
    def __init__(self,run):
        super(RunTab, self).__init__()
        self.run = run
        self.current_phase = 0
        self.current_phase_item = None
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)

        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()

        # properties layout
        properties_layout = QtGui.QHBoxLayout()
        
        # network design layouts: first vertical layout for everything
        net_design_layout = QtGui.QVBoxLayout()
        # 1) layout for group editing controls
        ge_layout = QtGui.QFormLayout()
        # 2) layout for wiring controls
        wc_layout = QtGui.QHBoxLayout()
        # 3) for group property controls in a single row
        group_layout = QtGui.QHBoxLayout()

        # parameter set layouts: first a main horizontal layout for everything
        h_phase_layout = QtGui.QHBoxLayout()
        # 1) layouts for phase editing controls
        ph_edit_layout = QtGui.QVBoxLayout()
        # 2) layout for parameter set (training and/or testing) editing controls
        self.pset_layout = QtGui.QVBoxLayout()
        

        #..............................................................
        # TAB WIDGET
        # create tab widget that divides this larger tab
        self.tab_divider = QtGui.QTabWidget()

        # create blank widgets for each subsection
        properties_widget = QtGui.QWidget(self)
        properties_widget.setLayout(properties_layout)
        net_design_widget = QtGui.QWidget(self)
        net_design_widget.setLayout(net_design_layout)
        parameter_sets_widget = QtGui.QWidget(self)
        parameter_sets_widget.setLayout(h_phase_layout)

        self.tab_divider.addTab(properties_widget,'Run Properties')
        self.tab_divider.addTab(net_design_widget,'Groups and Connections')
        self.tab_divider.addTab(parameter_sets_widget,'Events')
        

        #..............................................................
        # WIRING WIDGET
        self.wiring = CustomWiringWidget(self,run)

        # create wiring controls
        self.add_group_btn = QtGui.QPushButton('Add Group')
        self.delete_group_btn = QtGui.QPushButton('Delete Group')
        self.delete_group_btn.setEnabled(False)
        self.visualize_btn = QtGui.QPushButton('Visualize')
        if pydot.find_graphviz():
            pass
        else:
            self.visualize_btn.setEnabled(False)
        self.wire_helper = QtGui.QLabel("Click a group name to select group. Click a color cell to toggle connection.")
        
        wc_layout.addWidget(QtGui.QLabel('Network Adjacency Matrix:'))
        wc_layout.addWidget(self.add_group_btn)
        wc_layout.addWidget(self.delete_group_btn)
        wc_layout.addWidget(self.visualize_btn)
        wc_layout.addStretch(1)
        wc_layout.addWidget(self.wire_helper)

        # connect signals
        self.add_group_btn.clicked.connect(self.wiring.newGroup)
        self.delete_group_btn.clicked.connect(self.wiring.deleteGroup)
        self.visualize_btn.clicked.connect(self.visualizeNet)

        #..............................................................
        # GROUP DATA CONTROLS
        self.group_edit = QtGui.QGroupBox('Group Properties')
        self.group_edit.setAlignment(QtCore.Qt.AlignHCenter)
        self.group_name = QtGui.QLineEdit()
        self.group_name.setEnabled(False)
        self.group_units = QtGui.QSpinBox()
        self.group_units.setMinimum(0)
        self.group_units.setMaximum(10000)
        self.group_units.setEnabled(False)
        self.group_activation_type = QtGui.QComboBox()
        self.group_activation_type.addItem('LOGISTIC_ACTIVATION')
        self.group_activation_type.addItem('TANH_ACTIVATION')
        self.group_activation_type.setEnabled(False)
        self.group_error_type = QtGui.QComboBox()
        self.group_error_type.addItem('SUM_SQUARED_ERROR')
        self.group_error_type.addItem('CROSS_ENTROPY_ERROR')
        self.group_error_type.setEnabled(False)

        ge_layout.addRow('Name',self.group_name)
        ge_layout.addRow('Units',self.group_units)
        ge_layout.addRow('Activation type',self.group_activation_type)
        ge_layout.addRow('Error type',self.group_error_type)

        self.group_edit.setLayout(ge_layout)

        # connect signals
        self.group_name.editingFinished.connect(lambda:
                                    self.wiring.setGroupProperty('name',
                                                    self.group_name.text()))
        self.group_units.valueChanged.connect(lambda:
                                    self.wiring.setGroupProperty('units',
                                                    self.group_units.value()))
        self.group_activation_type.currentIndexChanged.connect(lambda i:
                                self.wiring.setGroupProperty('activation_type',
                                self.group_activation_type.itemText(i)))
        self.group_error_type.currentIndexChanged.connect(lambda i:
                         self.wiring.setGroupProperty('error_computation_type',
                                self.group_error_type.itemText(i)))
                                            

        #..............................................................
        # RUN-LEVEL DATA
        # create run-level data controls
        self.run_form = QtGui.QFormLayout()
        
        name_lab,self.name_box = self.run.getParameter('run_name').getWidget()
        seed_lab,self.seed_box = self.run.getParameter('seed').getWidget()
        ticks_lab,self.ticks_box = self.run.getParameter('ticks').getWidget()
        range_lab,self.range_box = self.run.getParameter('weight_range').getWidget()
        bias_lab,self.bias_box = self.run.getParameter('bias_value').getWidget()

        self.run_form.addRow(name_lab,self.name_box)
        self.run_form.addRow(seed_lab,self.seed_box)
        self.run_form.addRow(ticks_lab,self.ticks_box)
        self.run_form.addRow(range_lab,self.range_box)
        self.run_form.addRow(bias_lab,self.bias_box)

        # connect signals
        # NOTE: no need to send signlas to update data changes...widgets are tied to the
        # model data automatically...in this case you only have to update the tab label
        self.name_box.editingFinished.connect(self.run.getGUI().getMainTabs().refreshTabNames)

        #..............................................................
        # PHASE-LEVEL DATA
        phases = QtGui.QGroupBox('Interleaving and multi-phase control')
        phases.setAlignment(QtCore.Qt.AlignHCenter)
        
        self.phase_table = CustomPhaseWidget(self,run)
        self.add_phase_btn = QtGui.QPushButton('Add Phase')
        self.dup_phase_btn = QtGui.QPushButton('Duplicate Selected')
        self.delete_phase_btn = QtGui.QPushButton('Remove Selected')
        ph_btn_layout = QtGui.QHBoxLayout()
        ph_btn_layout.addWidget(self.add_phase_btn)
        ph_btn_layout.addWidget(self.dup_phase_btn)
        ph_btn_layout.addWidget(self.delete_phase_btn)
        
        ph_what_btn = QtGui.QLabel('<qt><a href="http://dummytext.com/">What is This?</a></qt>')
        ph_what_btn.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        ph_what_btn.linkActivated.connect(self.phaseWhat)
        ph_edit_layout.addLayout(ph_btn_layout)
        ph_edit_layout.addWidget(QtGui.QLabel('Double-click name to edit.'))
        ph_edit_layout.addWidget(self.phase_table)
        ph_edit_layout.addWidget(ph_what_btn)

        phases.setLayout(ph_edit_layout)

        # connect signals
        self.add_phase_btn.clicked.connect(self.phase_table.addPhase)
        self.dup_phase_btn.clicked.connect(self.phase_table.duplicatePhase)
        self.delete_phase_btn.clicked.connect(self.phase_table.deletePhase)

        #..............................................................
        # PHASE ITEM DATA
        self.pset = QtGui.QGroupBox('Phase Timeline')
        self.pset.setAlignment(QtCore.Qt.AlignHCenter)

        self.new_phase_item_btn = QtGui.QPushButton('Add Train/Test Event')
        self.edit_phase_item_btn = QtGui.QPushButton('Edit Selected')
        self.edit_phase_item_btn.setEnabled(False)
        self.delete_phase_item_btn = QtGui.QPushButton('Remove Selected')
        self.delete_phase_item_btn.setEnabled(False)
        self.dup_phase_item_btn = QtGui.QPushButton('Duplicate Selected')
        self.dup_phase_item_btn.setEnabled(False)

        pset_btn_layout1 = QtGui.QHBoxLayout()
        pset_btn_layout1.addWidget(self.new_phase_item_btn)
        pset_btn_layout1.addWidget(self.delete_phase_item_btn)
        pset_btn_layout2 = QtGui.QHBoxLayout()
        pset_btn_layout2.addWidget(self.edit_phase_item_btn)
        pset_btn_layout2.addWidget(self.dup_phase_item_btn)
        
        self.pset_layout.addLayout(pset_btn_layout1)
        self.pset_layout.addLayout(pset_btn_layout2)
        self.pset.setLayout(self.pset_layout)

        # connect signals
        self.new_phase_item_btn.clicked.connect(self.newPhaseItem)
        self.edit_phase_item_btn.clicked.connect(self.editPhaseItem)
        self.delete_phase_item_btn.clicked.connect(self.deletePhaseItem)
        self.dup_phase_item_btn.clicked.connect(self.duplicatePhaseItem)
        
        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(self.tab_divider)
        h_phase_layout.addWidget(phases)
        arrow_label = QtGui.QLabel(self)
        arrow_label.setPixmap(QtGui.QPixmap(os.path.join(os.getcwd(),'resources',
                                                         'images','right_arrow.png')))
        h_phase_layout.addWidget(arrow_label)
        h_phase_layout.addWidget(self.pset)
        net_design_layout.addLayout(wc_layout)
        net_design_layout.addWidget(self.wiring)
        net_design_layout.addLayout(group_layout)
        group_layout.addStretch(1)
        group_layout.addWidget(self.group_edit)
        group_layout.addStretch(1)
        properties_layout.addStretch(1)
        properties_layout.addLayout(self.run_form)
        properties_layout.addStretch(1)

    def refreshTabContents(self):
        self.phase_table.syncToRun()
        self.refreshChildPhaseWidgets()
        self.wiring.syncToRun()

    def refreshChildPhaseWidgets(self):
        for phase in self.run.getChildren():
            if phase.getWidget():
                phase.getWidget().syncToPhase()
            
    def getTabName(self):
        return str('Run Object: ' + self.run.getValueOf('run_name'))

    def updateTabName(self):
        self.run.getGUI().getMainTabs().refreshTabNames()

    def setHelperText(self,text):
        self.wire_helper.setText(text)

    def phaseWhat(self,URL):
        ph_instructions = '''A phase provides a way to group together training and test sets.

You can define the phase order as sequential (default) or
probabilistic (to interleave training sets non-deterministically).

Use multiple phases ONLY if you want to interleave different sets
of parameters (ie. sets with different example files).'''
        dialogs.showInfo(self,ph_instructions)

    def registerPhaseWidget(self,w):
        self.pset_layout.insertWidget(self.pset_layout.count()-1,w)

    def updateGroupInfo(self,index):
        if index == None:
            self.group_name.setText('')
            self.group_name.setEnabled(False)
            self.group_units.setValue(0)
            self.group_units.setEnabled(False)
            self.group_activation_type.setEnabled(False)
            self.group_error_type.setEnabled(False)
            self.delete_group_btn.setEnabled(False)
        else:
            group = self.run.getGroups()[index]
            self.group_name.setText(group['name'])
            self.group_name.setEnabled(True)
            self.group_units.setValue(group['units'])
            self.group_units.setEnabled(True)
            activation = group['activation_type']
            actIndex = self.group_activation_type.findText(activation)
            self.group_activation_type.setCurrentIndex(actIndex)
            self.group_activation_type.setEnabled(True)
            error = group['error_computation_type']
            errorIndex = self.group_error_type.findText(error)
            self.group_error_type.setCurrentIndex(errorIndex)
            self.group_error_type.setEnabled(True)

            self.delete_group_btn.setEnabled(True)

    def updatePhaseInfo(self,index,phase_name):
        self.current_phase = index
        # rename the group box holding the phase timeline
        self.pset.setTitle(phase_name + ' timeline')
        for j,sibling in enumerate(self.run.getChildren()):
            if j == index:
                sibling.showWidget()
            else:
                sibling.hideWidget()

    def updatePhaseItemInfo(self,index):
        if index is not None:
            self.current_phase_item = index
            self.edit_phase_item_btn.setEnabled(True)
            self.dup_phase_item_btn.setEnabled(True)
            self.delete_phase_item_btn.setEnabled(True)
        else:
            self.current_phase_item = None
            self.edit_phase_item_btn.setEnabled(False)
            self.dup_phase_item_btn.setEnabled(False)
            self.delete_phase_item_btn.setEnabled(False)

    def newPhaseItem(self):
        phase = self.run.getChildren()[self.current_phase]
        phase.newPhaseItem() # will update its own widget

    def editPhaseItem(self):
        phase = self.run.getChildren()[self.current_phase]
        self.run.getGUI().getMainTabs().requestTab(phase.getChildren()[self.current_phase_item])
        self.run.getGUI().getMainTabs().switchCurrentTab(phase.getChildren()[self.current_phase_item])

    def duplicatePhaseItem(self):
        if not self.current_phase_item is None:
            phase = self.run.getChildren()[self.current_phase]
            current_item = phase.getChildren()[self.current_phase_item]
            the_copy = current_item.getCopy()
            the_copy.getParameter('item_name').value = str(current_item.getValueOf('item_name') +
                                                           ' - COPY')
            the_copy.parent = phase
            phase.getChildren().append(the_copy)
            the_copy.createTab()
            self.run.getGUI().updateAllTabs()

    def deletePhaseItem(self):
        phase = self.run.getChildren()[self.current_phase]
        # remove from the main tab view
        self.run.getGUI().getMainTabs().removeTabByObject(phase.getChildren()[self.current_phase_item])
        # unregister tab from GUI
        pitem = phase.getChildren().pop(self.current_phase_item)
        self.run.getGUI().unRegisterTabbedObject(pitem)
        # disable buttons that require a selected object
        self.updatePhaseItemInfo(None)
        # also you have to manually change current item in the phase item widget
        phase.getWidget().current_item = None
        # remove references in any parent iterators to this phase "event"
        traceNode = phase.parent.parent
        while True:
            if traceNode.getClassName() == 'MikenetIterator':
                if traceNode.getAppliedPaths() != 'ALL':
                    newPaths = [x for x in traceNode.getAppliedPaths() 
                               if x.split(':')[1] != pitem.getValueOf('item_name')]
                    traceNode.setAppliedPaths(newPaths)
                traceNode = traceNode.parent
            else:
               break
        # update display to match underlying data
        self.run.getGUI().updateAllTabs()

    def visualizeNet(self):
        tmp_fn = str(guts.getRandomString(8) + '.png')
        graph = pydot.Dot(graph_type='digraph')
        nodes = []
        for g in self.run.getGroups():
            nodes.append(pydot.Node(g['name']))
            graph.add_node(nodes[-1])
        matrix = self.run.getMatrix()
        for i in range(len(self.run.getGroups())):
            for j in range(len(self.run.getGroups())):
                if matrix[i][j] == 1:
                    graph.add_edge(pydot.Edge(nodes[i],nodes[j]))
        graph.write_png(tmp_fn)
        img = misc.imread(tmp_fn)
        pyplot.figure('MikeNetGUI - Network Visualization')
        pyplot.imshow(img)
        pyplot.axis('off')
        pyplot.title(self.run.getValueOf('run_name'))
        pyplot.show()
        os.remove(tmp_fn)
        
    def getLevel(self):
        return 1
    

class IteratorTab(QtGui.QWidget):
    def __init__(self,iterator):
        super(IteratorTab, self).__init__()
        self.iterator = iterator
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        # null initialize special objects for later
        self.rand_int = None
        self.rand_dbl = None
        self.rand_gauss = None
        self.rand_1_lab = None
        self.rand_1 = None
        self.rand_2_lab = None
        self.rand_2 = None
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        form_layout = QtGui.QFormLayout()
        bottom_layout = QtGui.QHBoxLayout()
        name_layout = QtGui.QFormLayout()
        
        #..............................................................
        # CONTROLS
        # first, name which does not depend on this iterator's child
        name_lab,self.name_box = self.iterator.getParameter('iterator_name').getWidget()
        name_layout.addRow(name_lab,self.name_box)

        # connect signal
        self.name_box.editingFinished.connect(self.iterator.getGUI().getMainTabs().refreshTabNames)

        # then there is a form which holds parameters which DO depend on the child
        # create form groupBox.
        self.form_box = QtGui.QGroupBox()        
        self.form_box.setAlignment(QtCore.Qt.AlignHCenter)
        self.form_holder_layout = QtGui.QVBoxLayout()
        self.form_box.setLayout(self.form_holder_layout)
        self.form_holder = None
        self.refreshForm()
        # actual form will go inside the box, added to the form holder layout
        # form holder is a widget
        # each time new widgets come into play, the old form holder is closed and a new one
        # is added to the form holder layout

        # in case this iterator has no associated run, display message
        self.no_run_msg = QtGui.QLabel('No run has been associated with this yet.\n' +
                                       'In the script timeline, click a run \n' +
                                       'and drag it into this iterator object.')
        self.no_run_msg.setAlignment(QtCore.Qt.AlignHCenter)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(name_layout)
        main_layout.addWidget(self.no_run_msg)
        main_layout.addLayout(bottom_layout)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.form_box)
        bottom_layout.addStretch(1)
        main_layout.addStretch(1)

    def setRun(self,run):
        if run:
            self.form_box.show()
            self.no_run_msg.hide()
            self.refreshForm()
        else:
            self.form_box.hide()
            self.no_run_msg.show()

    def refreshForm(self):
        if self.form_holder:
            self.form_holder.close()
        self.form_holder = QtGui.QWidget()
        form_layout = QtGui.QFormLayout()
        
        vary_lab,vary_menu_box = self.iterator.getParameter('varying').getWidget()
        form_layout.addRow(vary_lab,vary_menu_box)
        repeat_lab,repeat_box = self.iterator.getParameter('repeat').getWidget()
        form_layout.addRow(repeat_lab,repeat_box)
        # for group hidden units, create a new widget
        # to capture group name
        if self.iterator.varying_parameter:
            if self.iterator.varying_parameter.variable_name == 'hidden_units':
                hu_lab,hu_box = self.iterator.varying_parameter.getWidget()
                form_layout.addRow(hu_lab,hu_box)
            # make a box asking if a random value should be used
            random_box = QtGui.QCheckBox()
            form_layout.addRow('Use random values?',random_box)
            if self.iterator.getRandomFlag():
                random_box.setCheckState(QtCore.Qt.Checked)
                # random value boxes built here
                self.rand_int = QtGui.QRadioButton('Random int',self)
                if (self.iterator.getRandomFlag()[0] == 'int'
                    or self.iterator.varying_parameter.widget_type in ['int_spinbox','text_field']):
                    self.rand_int.setChecked(True)
                    self.rand_1_lab = QtGui.QLabel('min')
                    self.rand_1 = QtGui.QSpinBox()
                    self.rand_1.setMinimum(0)
                    self.rand_1.setMaximum(10000000)
                    self.rand_1.setValue(self.iterator.getRandomFlag()[1])
                    self.rand_2_lab = QtGui.QLabel('max')
                    self.rand_2 = QtGui.QSpinBox()
                    self.rand_2.setMinimum(0)
                    self.rand_2.setMaximum(10000000)
                    self.rand_2.setValue(self.iterator.getRandomFlag()[2])
                
                form_layout.addRow('',self.rand_int)
                if self.iterator.varying_parameter.widget_type == 'dbl_spinbox':
                    self.rand_dbl = QtGui.QRadioButton('Random double',self)
                    if self.iterator.getRandomFlag()[0] == 'double':
                        self.rand_dbl.setChecked(True)
                        self.rand_1_lab = QtGui.QLabel('min')
                        self.rand_1 = QtGui.QDoubleSpinBox()
                        self.rand_1.setMinimum(0)
                        self.rand_1.setMaximum(10000000)
                        if self.iterator.varying_parameter.decimals:
                            self.rand_1.setDecimals(self.iterator.varying_parameter.decimals)
                        else:
                            self.rand_1.setDecimals(3)
                        self.rand_1.setValue(self.iterator.getRandomFlag()[1])
                        self.rand_2_lab = QtGui.QLabel('max')
                        self.rand_2 = QtGui.QDoubleSpinBox()
                        self.rand_2.setMinimum(0)
                        self.rand_2.setMaximum(10000000)
                        if self.iterator.varying_parameter.decimals:
                            self.rand_2.setDecimals(self.iterator.varying_parameter.decimals)
                        else:
                            self.rand_2.setDecimals(3)
                        self.rand_2.setValue(self.iterator.getRandomFlag()[2])
                        
                    self.rand_gauss = QtGui.QRadioButton('Random gaussian',self)
                    if self.iterator.getRandomFlag()[0] == 'gaussian':
                        self.rand_gauss.setChecked(True)
                        self.rand_1_lab = QtGui.QLabel('mu')
                        self.rand_1 = QtGui.QDoubleSpinBox()
                        self.rand_1.setMinimum(0)
                        self.rand_1.setMaximum(10000000)
                        if self.iterator.varying_parameter.decimals:
                            self.rand_1.setDecimals(self.iterator.varying_parameter.decimals)
                        else:
                            self.rand_1.setDecimals(3)
                        self.rand_1.setValue(self.iterator.getRandomFlag()[1])
                        self.rand_2_lab = QtGui.QLabel('sigma')
                        self.rand_2 = QtGui.QDoubleSpinBox()
                        self.rand_2.setMinimum(0)
                        self.rand_2.setMaximum(10000000)
                        if self.iterator.varying_parameter.decimals:
                            self.rand_2.setDecimals(self.iterator.varying_parameter.decimals)
                        else:
                            self.rand_2.setDecimals(3)
                        self.rand_2.setValue(self.iterator.getRandomFlag()[2])

                    form_layout.addRow('',self.rand_dbl)
                    form_layout.addRow('',self.rand_gauss)
                    # connect toggle signals after they are all initialized
                    self.rand_dbl.toggled.connect(self.toggledRandomRadios)
                    self.rand_gauss.toggled.connect(self.toggledRandomRadios)
                    self.rand_int.toggled.connect(self.toggledRandomRadios)
                else:
                    self.rand_dbl = None
                    self.rand_gauss = None
                    self.rand_int.setChecked(True) # don't connect signal
                    self.rand_int.setEnabled(False)
                    
                form_layout.addRow(self.rand_1_lab,self.rand_1)
                form_layout.addRow(self.rand_2_lab,self.rand_2)
                # special signals
                self.rand_1.valueChanged.connect(lambda: self.setSpecialRandValue(1,
                                                                    self.rand_1.value()))

                self.rand_2.valueChanged.connect(lambda: self.setSpecialRandValue(2,
                                                                    self.rand_2.value()))
                    
            else:
                random_box.setCheckState(QtCore.Qt.Unchecked)
                init_lab,init_box = self.iterator.getParameter('initial_value').getWidget()
                delta_lab,delta_box = self.iterator.getParameter('delta').getWidget()
                form_layout.addRow(init_lab,init_box)
                form_layout.addRow(delta_lab,delta_box)
            random_box.stateChanged.connect(self.toggledRandom)
            
            # create widget to let user apply iteration to specific phase events
            self.apply_all = QtGui.QCheckBox('all events')
            if self.iterator.varying_parameter.variable_name in ['seed','bias_value',\
                                                 'weight_range','hidden_units']:
                self.iterator.setAppliedPaths('ALL')
                self.apply_all.setEnabled(False)
            if self.iterator.getAppliedPaths() == 'ALL':
                self.apply_all.setCheckState(QtCore.Qt.Checked)
            else:
                self.apply_all.setCheckState(QtCore.Qt.Unchecked)
            form_layout.addRow('Apply to',self.apply_all)
            self.apply_all.stateChanged.connect(self.toggleApplyAll)
            
            self.apply_box = CustomApplyIterationWidget(self.iterator)
            if self.iterator.getAppliedPaths() != 'ALL':
                self.apply_box.show()
            else:
                self.apply_box.hide()
            form_layout.addRow('',self.apply_box)
            
        
        # connect signal from varying box, because other widgets depend on the type
        # of parameter selected there
        vary_menu_box.currentIndexChanged.connect(lambda i: self.varyingChanged(i))
        # and connect signal from applied paths checkbox
        self.form_holder.setLayout(form_layout)
        self.form_holder_layout.addWidget(self.form_holder)
        self.form_holder.show()
        
    def toggleApplyAll(self,state):
        if state == QtCore.Qt.Checked:
            self.apply_box.hide()
            self.iterator.setAppliedPaths('ALL')
        else:
            self.iterator.setAppliedPaths([])
            self.apply_box.updateLines()
            self.apply_box.show()

    def toggledRandom(self,i):
        if i == QtCore.Qt.Checked:
            self.iterator.setRandomFlag(['int',0,0])
        else:
            self.iterator.setRandomFlag(None)
        self.refreshForm()

    def toggledRandomRadios(self,b):
        if self.rand_int.isChecked():
            if self.iterator.getRandomFlag():
                self.iterator.getRandomFlag()[0] = 'int'
            else:
                self.iterator.setRandomFlag(['int',0,0])
        if self.rand_dbl:
            if self.rand_dbl.isChecked():
                if self.iterator.getRandomFlag():
                    self.iterator.getRandomFlag()[0] = 'double'
                else:
                    self.iterator.setRandomFlag(['double',0,0])
            elif self.rand_gauss.isChecked():
                if self.iterator.getRandomFlag():
                    self.iterator.getRandomFlag()[0] = 'gaussian'
                else:
                    self.iterator.setRandomFlag(['gaussian',0,0])
        self.refreshForm()

    def setSpecialRandValue(self,i,value):
        self.iterator.getRandomFlag()[i] = value

    def varyingChanged(self,i):
        self.iterator.updateDependentFields(i)
        self.iterator.getGUI().getScript().getTabWidget().refreshTabContents()
    
    def refreshTabContents(self):
        self.iterator.syncToRun()

    def getTabName(self):
        return str('Iterator Object: ' + self.iterator.getValueOf('iterator_name'))

    def updateTabName(self):
        self.iterator.getGUI().getMainTabs().refreshTabNames()

    def getLevel(self):
        return 1

class PhaseItemTab(QtGui.QWidget):
    def __init__(self,phase_item):
        super(PhaseItemTab, self).__init__()
        self.phase_item = phase_item
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)

        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()

        # properties layout (on its own tab)
        properties_layout = QtGui.QHBoxLayout()
        
        # network component layout (on its own tab)
        components_layout = QtGui.QVBoxLayout()

        # recording layout (on its own tab)
        recording_layout = QtGui.QVBoxLayout()
        
        # noise layout (on its own tab)
        noise_layout = QtGui.QHBoxLayout()
        

        #..............................................................
        # TAB WIDGET
        # create tab widget that divides this larger tab
        self.tab_divider = QtGui.QTabWidget()

        # create blank widgets for each subsection
        properties_widget = QtGui.QWidget(self)
        properties_widget.setLayout(properties_layout)
        components_widget = QtGui.QWidget(self)
        components_widget.setLayout(components_layout)
        recording_widget = QtGui.QWidget(self)
        recording_widget.setLayout(recording_layout)
        noise_widget = QtGui.QWidget(self)
        noise_widget.setLayout(noise_layout)

        self.tab_divider.addTab(properties_widget,'Event Properties')
        self.tab_divider.addTab(components_widget,'Isolate Network Components')
        self.tab_divider.addTab(recording_widget,'Setup Activation Recording')
        self.tab_divider.addTab(noise_widget,'Noise Control')
        

        #..............................................................
        # PHASE ITEM PROPERTIES
        # create controls
        self.item_form = QtGui.QFormLayout()
        
        name_lab,self.name_box = self.phase_item.getParameter('item_name').getWidget()
        prob_lab,self.prob_box = self.phase_item.getParameter('probability').getWidget()
        

        self.item_form.addRow(name_lab,self.name_box)
        self.item_form.addRow(prob_lab,self.prob_box)
        prob_comment = QtGui.QLabel(self.phase_item.getParameter('probability').comment)
        prob_comment.font().setItalic(True)
        self.item_form.addRow(QtGui.QLabel(''),prob_comment)
        # the following controls are not part of the parameters dict of this phase_item
        # so they need to be manually set up

        # test sets
        self.test_box = CustomTestSetSelectionWidget(self.phase_item)
        self.item_form.addRow('Link to test set(s)',self.test_box)
        
        # mode
        mode_box = QtGui.QGroupBox()
        mode_layout = QtGui.QHBoxLayout()
        self.mode_train_btn = QtGui.QRadioButton('Train')
        self.mode_test_btn = QtGui.QRadioButton('Test')
        if self.phase_item.getMode() == 'TRAIN':
            self.mode_train_btn.setChecked(True)
        else:
            self.mode_test_btn.setChecked(True)
        mode_layout.addWidget(self.mode_train_btn)
        mode_layout.addWidget(self.mode_test_btn)
        mode_box.setLayout(mode_layout)

        self.item_form.addRow('Mode',mode_box)

        self.profile_box = QtGui.QComboBox()
        self.profile_box_lab = QtGui.QLabel('Link to training set')
        self.item_form.addRow(self.profile_box_lab,self.profile_box)
        
        self.profile_name = QtGui.QLabel()
        self.profile_name.setText(self.phase_item.getProfile())
        self.profile_name_lab = QtGui.QLabel('Set')
        self.item_form.addRow(self.profile_name_lab,self.profile_name)

        self.override_box = QtGui.QGroupBox('Parameter Overrides')
        self.override_layout = QtGui.QVBoxLayout()
        self.override_box.setAlignment(QtCore.Qt.AlignHCenter)
        self.override_box.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.override_box.setLayout(self.override_layout)
        self.override_layout.addWidget(QtGui.QLabel('Click any value to override that parameter.\n' +
                                                    'Parameters with overrides are highlighted in yellow. ' +
                                                    'To undo, click the value again.'))
        self.parameter_view = None
        self.override_box.hide()
        if self.phase_item.getMode() == 'TEST':
            self.profile_name.hide()
            self.profile_box.hide()
            self.profile_name_lab.hide()
            self.profile_box_lab.hide()

        # connect signals
        # NOTE: no need to send signlas to update data changes...widgets are tied to the
        # model data automatically...in this case you only have to update the tab label
        self.name_box.editingFinished.connect(self.phase_item.getGUI().getMainTabs().refreshTabNames)
        self.mode_train_btn.toggled.connect(self.modeChanged)
        self.profile_box.currentIndexChanged.connect(self.profileChanged)

        #..............................................................
        # NET COMPONENTS
        self.components = CustomComponentSelectionWidget(self,self.phase_item)
        wc_layout = QtGui.QHBoxLayout()
        self.visualize_btn = QtGui.QPushButton('Visualize')
        if pydot.find_graphviz():
            pass
        else:
            self.visualize_btn.setEnabled(False)
        self.wire_helper = QtGui.QLabel("Click a group name to select group. Click a color cell to toggle connection.")

        # connect signals
        self.visualize_btn.clicked.connect(self.visualizeNet)

        #..............................................................
        # RECORDING SETUP
        self.recording = CustomRecordingWidget(self,self.phase_item)
        
        #..............................................................
        # NOISE CONTROLS
        # weight noise
        w_n_layout = QtGui.QVBoxLayout()
        w_n_box = QtGui.QGroupBox('Weight Noise')
        w_n_box.setAlignment(QtCore.Qt.AlignHCenter)
        w_n_box.setLayout(w_n_layout)
        self.weight_noise = CustomWeightNoiseWidget(self.phase_item)
        w_n_layout.addWidget(self.weight_noise)
        
        # input noise
        i_n_layout = QtGui.QVBoxLayout()
        i_n_box = QtGui.QGroupBox('Input Noise')
        i_n_box.setAlignment(QtCore.Qt.AlignHCenter)
        i_n_box.setLayout(i_n_layout)
        self.input_noise = CustomInputNoiseWidget(self.phase_item)
        i_n_layout.addWidget(self.input_noise)
        
        # activation noise
        a_n_layout = QtGui.QVBoxLayout()
        a_n_box = QtGui.QGroupBox('Activation Noise')
        a_n_box.setAlignment(QtCore.Qt.AlignHCenter)
        a_n_box.setLayout(a_n_layout)
        self.activation_noise = CustomActivationNoiseWidget(self.phase_item)
        a_n_layout.addWidget(self.activation_noise)
        
        
        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(self.tab_divider)
        properties_layout.addStretch(1)
        properties_layout.addLayout(self.item_form)
        properties_layout.addWidget(self.override_box)
        properties_layout.addStretch(1)
        components_layout.addLayout(wc_layout)
        wc_layout.addWidget(self.visualize_btn)
        wc_layout.addStretch(1)
        wc_layout.addWidget(self.wire_helper)
        components_layout.addWidget(self.components)
        recording_layout.addWidget(self.recording)
        noise_layout.addWidget(w_n_box)
        noise_layout.addWidget(i_n_box)
        noise_layout.addWidget(a_n_box)

    def modeChanged(self,b):
        self.phase_item.setMode(b)
        if b:
            self.profile_box.show()
            self.profile_name.show()
            self.profile_box_lab.show()
            self.profile_name_lab.show()
            self.refreshTrainingProfile()
            # this should update the parameter view and everything else automatically
        else:
            # hide training stuff
            self.override_box.hide()
            self.profile_box.hide()
            self.profile_name.hide()
            self.profile_box_lab.hide()
            self.profile_name_lab.hide()
            self.refreshTrainingProfile()

    def profileChanged(self,i):
        name = self.profile_box.itemText(i)
        self.profile_name.setText(name)
        self.phase_item.setProfile(name)
        self.refreshParameterView()

    def refreshParameterView(self):
        if self.parameter_view:
            try:
                self.parameter_view.close()
            except:
                # sometimes it complains that the C++ object has already been deleted
                pass
        if self.phase_item.getMode() == 'TEST':
            self.override_box.hide()
            return
        profile = self.phase_item.getGUI().getScript().getProfileByName(self.profile_name.text())
        if not profile:
            self.override_box.hide()
            return
        # update parameter view...
        # profile SHOULD be a training profile, but if for some reason a test profile
        # has the same name, it will screw it up...catch that here
        if profile.getClassName() != 'MikenetTrainingProfile':
            self.override_box.hide()
            return
        self.override_box.show()
        self.parameter_view = QtGui.QTabWidget()
        self.parameter_view.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.override_layout.addWidget(self.parameter_view)
        for category in profile.getCategories():
            cat_v_layout = QtGui.QVBoxLayout()
            cat_tab = QtGui.QWidget(self)

            cat_params = [x for x in profile.getAllParameters()
                          if x.category == category]
            
            cat_v_layout.addWidget(CustomInteractiveParamWidget(cat_params,
                                                                self.phase_item))
            cat_v_layout.addStretch(1)

            cat_tab.setLayout(cat_v_layout)
            self.parameter_view.addTab(cat_tab,category)
        
    def refreshTrainingProfile(self):
        train_profiles = self.phase_item.getGUI().getScript().getTrainingProfiles()
        old_name = self.phase_item.getProfile()

        self.profile_box.clear()
        
        old_deleted = True
        for prof in train_profiles.getChildren():
            self.profile_box.addItem(prof.getValueOf('profile_name'))
            if prof.getValueOf('profile_name') == old_name:
                old_deleted = False

        if not old_deleted:
            self.profile_box.setCurrentIndex(self.profile_box.findText(old_name))

    def visualizeNet(self):
        run = self.phase_item.parent.parent
        tmp_fn = str(guts.getRandomString(8) + '.png')
        graph = pydot.Dot(graph_type='digraph')
        nodes = []
        for g in run.getGroups():
            if g['name'] in self.phase_item.getComponentGroups():
                nodes.append(pydot.Node(g['name'],style="filled",fillcolor="green"))
            else:
                nodes.append(pydot.Node(g['name']))
            graph.add_node(nodes[-1])
        matrix = self.phase_item.getComponentMatrix()
        for i in range(len(matrix)):
            for j in range(len(run.getGroups())):
                if matrix[i][j] == 1:
                    graph.add_edge(pydot.Edge(nodes[i],nodes[j]))
                elif matrix[i][j] == 2:
                    graph.add_edge(pydot.Edge(nodes[i],nodes[j],color="green"))
        graph.write_png(tmp_fn)
        img = misc.imread(tmp_fn)
        pyplot.figure('MikeNetGUI - Network Visualization')
        pyplot.imshow(img)
        pyplot.axis('off')
        pyplot.title(run.getValueOf('run_name'))
        pyplot.show()
        os.remove(tmp_fn)

    def refreshTabContents(self):
        self.components.syncToRun()
        self.recording.syncToRun()
        self.updateNoiseControls()
        self.refreshTrainingProfile()
        self.test_box.syncToPhaseItem()
        
    def updateNoiseControls(self):
        self.weight_noise.syncToPhaseItem()
        self.input_noise.syncToPhaseItem()
        self.activation_noise.syncToPhaseItem()

    def setHelperText(self,text):
        self.wire_helper.setText(text)

    def getTabName(self):
        return str('Event: ' + self.phase_item.getValueOf('item_name'))

    def updateTabName(self):
        self.run.getGUI().getMainTabs().refreshTabNames()

    def getLevel(self):
        return 2

class ProfilesTab(QtGui.QWidget):
    def __init__(self,script):
        super(ProfilesTab, self).__init__()
        # layout
        main_layout = QtGui.QHBoxLayout()
        self.train = TrainingProfilesTab(script)
        self.test = TestProfilesTab(script)

        # training box
        train_layout = QtGui.QVBoxLayout()
        train_box = QtGui.QGroupBox('Training Sets')
        train_box.setAlignment(QtCore.Qt.AlignHCenter)
        train_box.setLayout(train_layout)
        train_layout.addWidget(self.train)

        # test box
        test_layout = QtGui.QVBoxLayout()
        test_box = QtGui.QGroupBox('Test Sets')
        test_box.setAlignment(QtCore.Qt.AlignHCenter)
        test_box.setLayout(test_layout)
        test_layout.addWidget(self.test)

        # putting it all together
        main_layout.addWidget(train_box)
        main_layout.addWidget(test_box)
        self.setLayout(main_layout)

    def refreshTabContents(self):
        self.train.refreshTabContents()
        self.test.refreshTabContents()                   


class TrainingProfilesTab(QtGui.QWidget):
    def __init__(self,script):
        super(TrainingProfilesTab, self).__init__()
        self.script = script
        self.current_profile = None

        #..............................................................
        # LAYOUTS
        # create main horizontal layout
        main_layout = QtGui.QVBoxLayout()
        # left and right column layouts
        top_layout = QtGui.QVBoxLayout()
        bottom_layout = QtGui.QHBoxLayout()
        # control buttons
        control_layout = QtGui.QGridLayout()

        #..............................................................
        # LIST VIEW OBJECT (ENTIRE LEFT COLUMN)
        # see custom_widgets module for CustomListWidget definitions
        self.list_view = CustomListWidget(self,script.getTrainingProfiles())

        #..............................................................
        # EDITING CONTROLS (ADD PROFILE, REMOVE, ETC...)
        # create editing buttons
        self.new_btn = QtGui.QPushButton('New Training Set')
        self.del_btn = QtGui.QPushButton('Remove Set')
        self.del_btn.setEnabled(False)
        self.edit_btn = QtGui.QPushButton('Edit Selected')
        self.edit_btn.setEnabled(False)
        self.dup_btn = QtGui.QPushButton('Duplicate Selected')
        self.dup_btn.setEnabled(False)

        # create timeline editing group box
        control = QtGui.QGroupBox()
        control_layout.setSpacing(10)
        control_layout.addWidget(self.new_btn,0,0,1,1)
        control_layout.addWidget(self.del_btn,0,1,1,1)
        control_layout.addWidget(self.edit_btn,1,0,1,1)
        control_layout.addWidget(self.dup_btn,1,1,1,1)
        control.setLayout(control_layout)

        # connect button signals
        self.new_btn.clicked.connect(self.newProfile)
        self.edit_btn.clicked.connect(self.editProfile)
        self.dup_btn.clicked.connect(self.duplicateProfile)
        self.del_btn.clicked.connect(self.removeProfile)
        
        #..............................................................                 
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(top_layout)
        top_layout.addWidget(self.list_view)
        main_layout.addLayout(bottom_layout)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(control)
        bottom_layout.addStretch(1)

        self.list_view.syncToModel()

    def updateProfileInfo(self,profile):
        self.current_profile = profile
        self.script.getGUI().updateAllTabs()
        if profile:
            self.edit_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.dup_btn.setEnabled(True)
        else:
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.dup_btn.setEnabled(False)

    def newProfile(self):
        self.script.newTrainingProfile()
        self.list_view.syncToModel()
        self.script.getGUI().updateAllTabs()

    def duplicateProfile(self):
        if self.current_profile:
            the_copy = self.current_profile.getCopy()
            the_copy.parent = self.current_profile.parent
            i = the_copy.parent.getChildren().index(self.current_profile)
            the_copy.parent.getChildren().insert(i+1,the_copy)
        self.list_view.syncToModel()

    def editProfile(self):
        self.current_profile.getEditWindow()

    def removeProfile(self):
        if self.current_profile:
            self.script.removeTrainingProfile(self.current_profile)
        self.updateProfileInfo(None)
        self.list_view.syncToModel()
        self.script.getGUI().updateAllTabs()

    def refreshTabContents(self):
        self.list_view.syncToModel()
        pass
    
    def getTabName(self):
        return 'Training Sets'

    def getLevel(self):
        return 0

class TestProfilesTab(QtGui.QWidget):
    def __init__(self,script):
        super(TestProfilesTab, self).__init__()
        self.script = script
        self.current_profile = None

        #..............................................................
        # LAYOUTS
        # create main horizontal layout
        main_layout = QtGui.QVBoxLayout()
        # left and right column layouts
        top_layout = QtGui.QVBoxLayout()
        bottom_layout = QtGui.QHBoxLayout()
        # control buttons
        control_layout = QtGui.QGridLayout()

        #..............................................................
        # LIST VIEW OBJECT (ENTIRE LEFT COLUMN)
        # see custom_widgets module for CustomListWidget definitions
        self.list_view = CustomListWidget(self,script.getTestProfiles())

        #..............................................................
        # EDITING CONTROLS (ADD PROFILE, REMOVE, ETC...)
        # create editing buttons
        self.new_btn = QtGui.QPushButton('New Test Set')
        self.del_btn = QtGui.QPushButton('Remove Set')
        self.del_btn.setEnabled(False)
        self.edit_btn = QtGui.QPushButton('Edit Selected')
        self.edit_btn.setEnabled(False)
        self.dup_btn = QtGui.QPushButton('Duplicate Selected')
        self.dup_btn.setEnabled(False)

        # create timeline editing group box
        control = QtGui.QGroupBox()
        control_layout.setSpacing(10)
        control_layout.addWidget(self.new_btn,0,0,1,1)
        control_layout.addWidget(self.del_btn,0,1,1,1)
        control_layout.addWidget(self.edit_btn,1,0,1,1)
        control_layout.addWidget(self.dup_btn,1,1,1,1)
        control.setLayout(control_layout)

        # connect button signals
        self.new_btn.clicked.connect(self.newProfile)
        self.edit_btn.clicked.connect(self.editProfile)
        self.dup_btn.clicked.connect(self.duplicateProfile)
        self.del_btn.clicked.connect(self.removeProfile)
        
        #..............................................................                 
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(top_layout)
        top_layout.addWidget(self.list_view)
        main_layout.addLayout(bottom_layout)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(control)
        bottom_layout.addStretch(1)

        self.list_view.syncToModel()

    def updateProfileInfo(self,profile):
        self.current_profile = profile
        if profile:
            self.edit_btn.setEnabled(True)
            self.del_btn.setEnabled(True)
            self.dup_btn.setEnabled(True)
        else:
            self.edit_btn.setEnabled(False)
            self.del_btn.setEnabled(False)
            self.dup_btn.setEnabled(False)
        

    def newProfile(self):
        self.script.newTestProfile()
        self.list_view.syncToModel()
        self.script.getGUI().updateAllTabs()

    def duplicateProfile(self):
        if self.current_profile:
            the_copy = self.current_profile.getCopy()
            the_copy.parent = self.current_profile.parent
            i = the_copy.parent.getChildren().index(self.current_profile)
            the_copy.parent.getChildren().insert(i+1,the_copy)
        self.list_view.syncToModel()

    def removeProfile(self):
        if self.current_profile:
            # remove references to this profile in all phase items
            self.DFS_removeProfile(self.script)
            self.script.removeTestProfile(self.current_profile)
        self.updateProfileInfo(None)
        self.list_view.syncToModel()
        self.script.getGUI().updateAllTabs()

    def DFS_removeProfile(self,node):
        for child in node.getChildren():
            if child.getClassName() == 'MikenetPhaseItem':
                name = self.current_profile.getValueOf('profile_name')
                if name in child.getTestProfiles():
                    child.getTestProfiles().remove(name)
            else:
                self.DFS_removeProfile(child)

    def editProfile(self):
        self.current_profile.getEditWindow()

    def refreshTabContents(self):
        self.list_view.syncToModel()
    
    def getTabName(self):
        return 'Test Sets'

    def getLevel(self):
        return 0
    
