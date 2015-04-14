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
from math import floor

class TrainingProfileEditor(QtGui.QDialog):
    def __init__(self,profile,gui):
        super(TrainingProfileEditor, self).__init__(gui)
        self.gui = gui
        self.training_profile = profile
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - ' + profile.getValueOf('profile_name'))
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # TRAINING PARAMETERS
        category_tabs = QtGui.QTabWidget(self)
        for category in self.training_profile.getCategories():
            cat_h_layout = QtGui.QHBoxLayout()
            cat_form = QtGui.QFormLayout()
            cat_tab = QtGui.QWidget(self)

            cat_params = [x for x in self.training_profile.getAllParameters()
                          if x.category == category]

            for param in cat_params:
                l_side, r_side = param.getWidget()
                cat_form.addRow(l_side, r_side)
                #if param.comment:
                #    if type(param.comment) == str:
                #        cat_form.addRow('',QtGui.QLabel(param.comment))
                #    else:
                #        cat_form.addRow('',param.comment)

            cat_tab.setLayout(cat_h_layout)
            cat_h_layout.addLayout(cat_form)
            category_tabs.addTab(cat_tab,category)

        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(category_tabs)
        main_layout.addLayout(button_layout)

    def okAction(self):
        self.gui.getScript().getProfilesTabWidget().refreshTabContents()
        self.accept()

    def cancelAction(self):
        for param in self.training_profile.getAllParameters():
            param.recover()
        
        self.reject()


class TestProfileEditor(QtGui.QDialog):
    def __init__(self,profile,gui):
        super(TestProfileEditor, self).__init__(gui)
        self.gui = gui
        self.test_profile = profile
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - ' + profile.getValueOf('profile_name'))
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        form_layout = QtGui.QFormLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # STUFF
        for p in self.test_profile.getAllParameters():
        	w1,w2 = p.getWidget()
        	form_layout.addRow(w1,w2)

        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)

    def okAction(self):
        self.gui.getScript().getProfilesTabWidget().refreshTabContents()
        self.accept()

    def cancelAction(self):
        for param in self.test_profile.getAllParameters():
            param.recover()
        
        self.reject()

class HLine(QtGui.QFrame):
    def __init__(self,parent):
        super(HLine, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                     QtGui.QSizePolicy.Fixed)
        self.setFrameShape(QtGui.QFrame.HLine)
        self.setFrameShadow(QtGui.QFrame.Sunken)

class LinkToTestEditor(QtGui.QDialog):
    def __init__(self,gui,phase_item):
        super(LinkToTestEditor, self).__init__(gui)
        self.phase_item = phase_item
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Link To Test Set')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # Test set selector widget
        self.test_set_menu = QtGui.QComboBox()
        # add all available test sets to the menu
        all_tests = gui.getScript().getTestProfiles().getChildren()
        for t in all_tests:
            self.test_set_menu.addItem(t.getValueOf('profile_name'))
            
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(self.test_set_menu)
        main_layout.addLayout(button_layout)

    def okAction(self):
        # make sure test isn't already added
        if self.test_set_menu.currentText() in self.phase_item.getTestProfiles():
            self.reject()
        else:
            # add test set to the phase item node
            self.phase_item.addTestProfile(self.test_set_menu.currentText())
            self.accept()

    def cancelAction(self):
        self.reject()


class OverrideEditor(QtGui.QDialog):
    def __init__(self,gui,param,phase_item):
        super(OverrideEditor, self).__init__(gui)
        # param is the parameter to override!
        self.param = param
        self.phase_item = phase_item
        
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Parameter Override')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        form_layout = QtGui.QFormLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # FORM
        form_layout.addRow('Parameter:',QtGui.QLabel(self.param.variable_name))
        form_layout.addRow(HLine(self))
        # old value
        old_val = None
        if self.param.widget_type == 'checkbox':
            if self.param.value == 0:
                old_val = 'Off'
            else:
                old_val = 'On'
        elif self.param.widget_type == 'dropdown':
            old_val = param.dropdown_options[param.value]
        else:
            old_val = param.value
        form_layout.addRow('Old value:',QtGui.QLabel(str(old_val)))
        # create widget to capture new value. depends on widget type
        self.new_val = None
        if self.param.widget_type == 'text_field':
            self.new_val = QtGui.QLineEdit()
        elif self.param.widget_type == 'int_spinbox':
            self.new_val = QtGui.QSpinBox()
            if self.param.minimum:
                self.new_val.setMinimum(self.param.minimum)
            if self.param.maximum:
                self.new_val.setMaximum(self.param.maximum)
            if self.param.step:
                self.new_val.setSingleStep(self.param.step)
        elif self.param.widget_type == 'dbl_spinbox':
            self.new_val = QtGui.QDoubleSpinBox()
            if self.param.minimum:
                self.new_val.setMinimum(self.param.minimum)
            if self.param.maximum:
                self.new_val.setMaximum(self.param.maximum)
            if self.param.step:
                self.new_val.setSingleStep(self.param.step)
            if self.param.decimals:
                self.new_val.setDecimals(self.param.decimals)
        elif self.param.widget_type == 'checkbox':
            self.new_val = QtGui.QCheckBox()
        elif self.param.widget_type == 'dropdown':
            self.new_val = QtGui.QComboBox()
            for option in self.param.dropdown_options:
                self.new_val.addItem(option)
        elif self.param.widget_type == 'path':
            self.new_val = QtGui.QLineEdit('/Enter new path here...')

        form_layout.addRow('New value:',self.new_val)
            
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)

    def sizeHint(self):
        return QtCore.QSize(2*self.fontMetrics().width('MikeNet GUI - Parameter Override'),
                            200)

    def okAction(self):
        # create new parameter (don't touch the original)
        paramDict = {'variable_name': self.param.variable_name,
                     'widget_type': self.param.widget_type}
        if self.param.comment:
            paramDict['comment'] = param.comment
        if self.param.widget_type == 'text_field':
            paramDict['value'] = self.new_val.text()
        elif self.param.widget_type == 'int_spinbox':
            paramDict['value'] = self.new_val.value()
            if self.param.minimum and self.param.maximum:
                paramDict['range'] = [self.param.minimum,
                                      self.param.maximum]
            if self.param.step:
                paramDict['step'] = self.param.step
        elif self.param.widget_type == 'dbl_spinbox':
            paramDict['value'] = self.new_val.value()
            if self.param.minimum and self.param.maximum:
                paramDict['range'] = [self.param.minimum,
                                      self.param.maximum]
            if self.param.step:
                paramDict['step'] = self.param.step
            if self.param.decimals:
                paramDict['decimals'] = self.param.decimals
        elif self.param.widget_type == 'checkbox':
            if self.new_val.checkState() == QtCore.Qt.Checked:
                paramDict['value'] = 1
            else:
                paramDict['value'] = 0
        elif self.param.widget_type == 'dropdown':
            paramDict['value'] = self.new_val.currentIndex()
            paramDict['dropdown_options'] = self.param.dropdown_options
        elif self.param.widget_type == 'path':
            paramDict['value'] = self.new_val.text()
            
        # add this param to the phase_item's overrides list
        self.phase_item.newOverride(paramDict)
        
        self.accept()

    def cancelAction(self):
        self.reject()

class PreferencesEditor(QtGui.QDialog):
    '''Unlike the OverrideEditor class, this changes the parameters in the GUI.

    However, if you don't also call the GUI's own 'savePreferences()',
    then the changes won't be permanently saved.
    '''
    def __init__(self,gui):
        super(PreferencesEditor, self).__init__(gui)
        # param is the parameter to override!
        self.gui = gui
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Program Preferences')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        app_layout = QtGui.QFormLayout()
        db_question = QtGui.QFormLayout()
        db_layout = QtGui.QFormLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # FORMS
        app_box = QtGui.QGroupBox('Application Settings')
        app_box.setAlignment(QtCore.Qt.AlignHCenter)
        app_box.setLayout(app_layout)

        mn_set,mn_path = self.gui.parameters['mikenet_path'].getWidget()
        app_layout.addRow(mn_set,mn_path)
        build_lab,build_box = self.gui.parameters['build_method'].getWidget()
        app_layout.addRow(build_lab,build_box)
        app_layout.addRow('',QtGui.QLabel(self.gui.parameters['build_method'].comment))
        multi_lab,multi_box = self.gui.parameters['multiprocessing'].getWidget()
        app_layout.addRow(multi_lab,multi_box)
        maxcpu_lab,self.maxcpu_box = self.gui.parameters['max_cpus'].getWidget()
        app_layout.addRow(maxcpu_lab,self.maxcpu_box)
        email_lab,email_box = self.gui.parameters['email_notification'].getWidget()
        app_layout.addRow(email_lab,email_box)
        address_lab,self.address_box = self.gui.parameters['email_address'].getWidget()
        app_layout.addRow(address_lab,self.address_box)

        usedb_lab,usedb_box = self.gui.parameters['use_database'].getWidget()
        db_question.addRow(usedb_lab,usedb_box)

        self.db_box = QtGui.QGroupBox('Database Settings')
        self.db_box.setAlignment(QtCore.Qt.AlignHCenter)
        self.db_box.setLayout(db_layout)

        db_set,db_path = self.gui.parameters['database_path'].getWidget()
        db_layout.addRow(db_set,db_path)
        db_layout.addRow('',QtGui.QLabel(self.gui.parameters['database_path'].comment))
        driver_lab,driver_box = self.gui.parameters['database_driver'].getWidget()
        db_layout.addRow(driver_lab,driver_box)
        host_lab,host_box = self.gui.parameters['database_host_name'].getWidget()
        db_layout.addRow(host_lab,host_box)
        user_lab,user_box = self.gui.parameters['database_user_name'].getWidget()
        db_layout.addRow(user_lab,user_box)
        pw_lab,pw_box = self.gui.parameters['database_password'].getWidget()
        db_layout.addRow(pw_lab,pw_box)

        # special signals
        usedb_box.stateChanged.connect(self.toggleDB)
        email_box.stateChanged.connect(self.toggleEmail)
        multi_box.stateChanged.connect(self.toggleMulti)

        if self.gui.parameters['use_database'].value == 1:
            self.db_box.setEnabled(True)
        else:
            self.db_box.setEnabled(False)
            
        if self.gui.parameters['email_notification'].value == 1:
            self.address_box.setEnabled(True)
        else:
            self.address_box.setEnabled(False)
            
        if self.gui.parameters['multiprocessing'].value == 1:
            self.maxcpu_box.setEnabled(True)
        else:
            self.maxcpu_box.setEnabled(False)
        
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(app_box)
        main_layout.addLayout(db_question)
        main_layout.addWidget(self.db_box)
        main_layout.addLayout(button_layout)

    def sizeHint(self):
        return QtCore.QSize(3*self.fontMetrics().width('MikeNet GUI - Program Preferences'),
                            200)

    def toggleDB(self,state):
        if state == QtCore.Qt.Checked:
            self.db_box.setEnabled(True)
        else:
            self.db_box.setEnabled(False)

    def toggleEmail(self,state):
        if state == QtCore.Qt.Checked:
            self.address_box.setEnabled(True)
        else:
            self.address_box.setEnabled(False)

    def toggleMulti(self,state):
        if state == QtCore.Qt.Checked:
            self.maxcpu_box.setEnabled(True)
        else:
            self.maxcpu_box.setEnabled(False)

    def okAction(self):
        self.gui.savePreferences()
        self.accept()

    def cancelAction(self):
        for p in self.gui.parameters.values():
            p.recover()
        self.reject()

class DefaultsEditor(QtGui.QDialog):
    def __init__(self,gui,script):
        super(DefaultsEditor, self).__init__(gui)
        # param is the parameter to override!
        self.script = script
        self.input_widgets= []
        
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setWindowTitle('MikeNet GUI - Set Default Parameters')
        
        #..............................................................
        # LAYOUTS
        # main layout
        main_layout = QtGui.QVBoxLayout()
        h_layout = QtGui.QHBoxLayout()
        l_form_layout = QtGui.QFormLayout()
        r_form_layout = QtGui.QFormLayout()
        button_layout = QtGui.QHBoxLayout()

        #..............................................................
        # FORM, put half on the left side and half on the right
        half = floor(len(script.getDefaults())/2)
        
        for i,d in enumerate(script.getDefaults()):
            # create widget to capture new value. depends on widget type
            new_val = None
            if d['widget_type'] == 'text_field':
                new_val = QtGui.QLineEdit()
                new_val.setText(d['value'])
            elif d['widget_type'] == 'int_spinbox':
                new_val = QtGui.QSpinBox()
                if 'range' in d:
                    new_val.setMinimum(d['range'][0])
                    new_val.setMaximum(d['range'][1])
                if 'step' in d:
                    new_val.setSingleStep(d['step'])
                new_val.setValue(int(d['value']))
            elif d['widget_type'] == 'dbl_spinbox':
                new_val = QtGui.QDoubleSpinBox()
                if 'range' in d:
                    new_val.setMinimum(d['range'][0])
                    new_val.setMaximum(d['range'][1])
                if 'step' in d:
                    new_val.setSingleStep(d['step'])
                if 'decimals' in d:
                    new_val.setDecimals(d['decimals'])
                new_val.setValue(float(d['value']))
            elif d['widget_type'] == 'checkbox':
                new_val = QtGui.QCheckBox()
                if d['value'] == 1:
                    new_val.setCheckState(QtCore.Qt.Checked)
            elif d['widget_type'] == 'dropdown':
                new_val = QtGui.QComboBox()
                if 'dropdown_options' in d:
                    for option in d['dropdown_options']:
                        new_val.addItem(option)
                new_val.setCurrentIndex(int(d['value']))
            self.input_widgets.append(new_val)
            if i <= half:
                l_form_layout.addRow(d['form_name'],new_val)
            else:
                r_form_layout.addRow(d['form_name'],new_val)
            
        #..............................................................
        # BUTTONS
        self.ok_btn = QtGui.QPushButton('Ok')
        self.ok_btn.setDefault(True)
        self.cancel_btn = QtGui.QPushButton('Cancel')
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)

        # connect button signals
        self.ok_btn.clicked.connect(self.okAction)
        self.cancel_btn.clicked.connect(self.cancelAction)

        #..............................................................
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addLayout(h_layout)
        h_layout.addLayout(l_form_layout)
        h_layout.addLayout(r_form_layout)
        main_layout.addLayout(button_layout)

    def sizeHint(self):
        return QtCore.QSize(1.5*self.fontMetrics().width('MikeNet GUI - Set Default Parameters'),
                            200)

    def okAction(self):
        for w,d in zip(self.input_widgets,self.script.getDefaults()):
            if d['widget_type'] == 'text_field':
                d['value'] = w.text()
            elif 'spinbox' in d['widget_type']:
                d['value'] = w.value()
            elif d['widget_type'] == 'dropdown':
                d['value'] = w.currentIndex()
            elif d['widget_type'] == 'checkbox':
                if w.checkState() == QtCore.Qt.Checked:
                    d['value'] = 1
                else:
                    d['value'] = 0
                    
        self.accept()

    def cancelAction(self):
        self.reject()
        

class ExamplePreviewer(QtGui.QWidget):
    def __init__(self,parent):
        super(ExamplePreviewer, self).__init__(parent)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                     QtGui.QSizePolicy.Expanding)

        self.flags = []

        # layouts
        main_layout = QtGui.QVBoxLayout()
        info_form = QtGui.QFormLayout()

        # empty label
        self.empty = QtGui.QLabel('...')

        # reading progress bar
        self.progress = QtGui.QProgressBar(self)
        self.progress.setMinimum(0)
        self.progress.setValue(0)
        self.progress.hide() # initially hidden
        self.progress_label = QtGui.QLabel('Reading example file...')
        self.progress_label.hide()

        # error details button
        self.see_details = QtGui.QPushButton('See details')
        self.see_details.clicked.connect(self.seeDetails)
        self.see_details.hide()

        # info widgets
        self.info = QtGui.QWidget(self)
        self.info.setLayout(info_form)

        self.proper = QtGui.QLabel('ok')
        self.num_examples = QtGui.QLabel('0')
        self.tick_min = QtGui.QLabel('1')
        self.clamp_groups = QtGui.QLabel('    ...')
        self.target_groups = QtGui.QLabel('    ...')

        info_form.addRow('Formatting:',self.proper)
        info_form.addRow('',self.see_details)
        info_form.addRow('Examples count:',self.num_examples)
        info_form.addRow('Time ticks:',self.tick_min)
        info_form.addRow(QtGui.QLabel('CLAMP Groups:'))
        info_form.addRow(self.clamp_groups)
        info_form.addRow(QtGui.QLabel('TARGET Groups:'))
        info_form.addRow(self.target_groups)

        self.info.hide() # initially hidden
        
        # putting it all together
        self.setLayout(main_layout)
        main_layout.addWidget(self.empty)
        main_layout.addWidget(self.progress_label)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(self.info)

    def readExample(self,ex_path):
        if not ex_path:
            return
        # hide everything but progress
        self.empty.hide()
        self.info.hide()
        self.progress_label.show()
        self.progress.setValue(0)
        self.progress.show()

        # read the file
        try:
            ex_file = open(ex_path,'r')
        except:
            dialogs.showError(self,('Problem opening file '+ex_path),
                              traceback.print_exc(file=sys.stdout))
            self.empty.show()
            self.info.hide()
            self.progress_label.hide()
            self.progress.hide()
            return
        
        ex_lines = ex_file.readlines()
        ex_file.close()
        self.progress.setMaximum(len(ex_lines))
        
        ex_count = 0
        tag_count = 0
        prob_count = 0
        clamp_data = []
        target_data = []
        tick_min = 1
        self.flags = []

        reading_type = None
        cur_data = ['    ',None,None,None,' units']

        for i,line in enumerate(ex_lines):
            self.progress.setValue(i+1)
            if 'TAG' in line:
                reading_type = None
                tag_count += 1

            elif 'PROB' in line:
                reading_type = None
                prob_count += 1
            
            elif 'CLAMP' in line:
                # whatever group data you were previously working on, save it first
                if reading_type:
                    if 'CLAMP' in reading_type:
                        clamp_data.append(tuple(cur_data))
                    elif 'TARGET' in reading_type:
                        target_data.append(tuple(cur_data))

                # found a group that will be clamped...get the name
                line_pieces = line.split()
                if len(line_pieces) < 4:
                    self.flags.append('- Improper CLAMP specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                    break
                if line_pieces[3] not in ['FULL','SPARSE']:
                    self.flags.append('- Improper CLAMP specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                    break
                cur_data[1] = '"'+line_pieces[1]+'"'
                # find out if there is a max tick time
                if line_pieces[2] != 'ALL':
                    digits = line_pieces[2].split('-')
                    try:
                        tick_min = int(digits[-1]) + 1
                    except:
                        self.flags.append('- Improper CLAMP specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                        break
                # get unit constraints to help user with number of units
                if line_pieces[3] == 'FULL':
                    reading_type = 'CLAMP FULL'
                    cur_data[2] = ', exactly '
                    cur_data[3] = len(line_pieces) - 4
                else:
                    reading_type = 'CLAMP SPARSE'
                    cur_data[2] = ', at least '
                    values = line_pieces[4:]
                    values = [int(x) for x in values]
                    cur_data[3] = max(values) + 1
                    
                if ';' in line:
                    # case where ; is not on its own line
                    ex_count += 1
                    # whatever group data you were previously working on, save it first
                    if reading_type:
                        if 'CLAMP' in reading_type:
                            clamp_data.append(tuple(cur_data))
                        elif 'TARGET' in reading_type:
                            target_data.append(tuple(cur_data))
                        reading_type = None
                
            elif 'TARGET' in line:
                # whatever group data you were previously working on, save it first
                if reading_type:
                    if 'CLAMP' in reading_type:
                        clamp_data.append(tuple(cur_data))
                    elif 'TARGET' in reading_type:
                        target_data.append(tuple(cur_data))

                # found a group that will be compared with a target...get the name
                line_pieces = line.split()
                if len(line_pieces) < 4:
                    self.flags.append('- Improper TARGET specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                    break
                if line_pieces[3] not in ['FULL','SPARSE']:
                    self.flags.append('- Improper TARGET specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                    break
                cur_data[1] = '"'+line_pieces[1]+'"'
                # find out if there is a max tick time
                if line_pieces[2] != 'ALL':
                    digits = line_pieces[2].split('-')
                    try:
                        tick_min = int(digits[-1]) + 1
                    except:
                        self.flags.append('- Improper TARGET specifier at line '+str(i+1)+
                                 '. See Help for proper formatting instructions.')
                        break
                # get unit constraints to help user with number of units
                if line_pieces[3] == 'FULL':
                    reading_type = 'TARGET FULL'
                    cur_data[2] = ', exactly '
                    cur_data[3] = len(line_pieces) - 4
                else:
                    reading_type = 'TARGET SPARSE'
                    cur_data[2] = ', at least '
                    values = line_pieces[4:]
                    values = [int(x) for x in values]
                    cur_data[3] = max(values) + 1
                    
                if ';' in line:
                    # case where ; is not on its own line
                    ex_count += 1
                    # whatever group data you were previously working on, save it first
                    if reading_type:
                        if 'CLAMP' in reading_type:
                            clamp_data.append(tuple(cur_data))
                        elif 'TARGET' in reading_type:
                            target_data.append(tuple(cur_data))
                        reading_type = None
                    
            elif ';\n' == line:
                ex_count += 1
                # whatever group data you were previously working on, save it first
                if reading_type:
                    if 'CLAMP' in reading_type:
                        clamp_data.append(tuple(cur_data))
                    elif 'TARGET' in reading_type:
                        target_data.append(tuple(cur_data))
                    reading_type = None

            elif line == '\n':
                # skip blank lines
                pass

            else:
                line_pieces = line.split()
                # add to unit constraints to help user with number of units
                # note that 4th value is a count for FULL and a max value for SPARSE
                if 'FULL' in reading_type:
                    cur_data[3] += len(line_pieces)
                else:
                    values = line_pieces[:]
                    values = [int(x) for x in values]
                    cur_data[3] = max(values) + 1

                if ';' in line:
                    # case where ; is not on its own line
                    ex_count += 1
                    # whatever group data you were previously working on, save it first
                    if reading_type:
                        if 'CLAMP' in reading_type:
                            clamp_data.append(tuple(cur_data))
                        elif 'TARGET' in reading_type:
                            target_data.append(tuple(cur_data))
                        reading_type = None

        # catch some errors
        if tag_count > 0 and tag_count != ex_count:
            self.flags.append('- Possible TAG mismatch. Counted '+str(tag_count)+
                              ' TAGs and '+str(ex_count)+' semicolons.')
        if prob_count > 0 and prob_count != ex_count:
            self.flags.append('- Possible PROB mismatch. Counted '+str(prob_count)+
                              '  PROBs and '+str(ex_count)+' semicolons.')

        clamp_data = list(set(clamp_data))
        target_data = list(set(target_data))
        
        c_exactlies = [x for x in clamp_data if 'exactly' in x[2]]
        t_exactlies = [x for x in target_data if 'exactly' in x[2]]

        # find group unit mismatches
        unique_names = [x[1] for x in c_exactlies]
        if len(unique_names) != len(set(unique_names)):
            self.flags.append('- Inconsistent group unit counts using CLAMP FULL.')
            for x in unique_names:
                self.flags.append('    '+x)
        unique_names = [x[1] for x in t_exactlies]
        if len(unique_names) != len(set(unique_names)):
            self.flags.append('- Inconsistent group unit counts using TARGET FULL.')
            for x in unique_names:
                self.flags.append('    '+x)

        # convert tuples into strings
        clamp_data = [(x[0],x[1],x[2],str(x[3]),x[4]) for x in clamp_data]
        target_data = [(x[0],x[1],x[2],str(x[3]),x[4]) for x in target_data]
        clamp_data = [''.join(x) for x in clamp_data]
        target_data = [''.join(x) for x in target_data]
        
        # update informative text labels
        if self.flags:
            self.proper.setText('errors')
            self.proper.setStyleSheet('color: red')
            self.see_details.show()
        else:
            self.proper.setText('ok')
            self.proper.setStyleSheet('color: black')
            self.see_details.hide()
            
        self.num_examples.setText(str(ex_count))
        g_txt = '\n'.join(clamp_data)
        self.clamp_groups.setText(g_txt)
        t_txt = '\n'.join(target_data)
        self.target_groups.setText(t_txt)
        self.tick_min.setText('at least '+ str(tick_min))

        # hide progress bar and show information
        self.empty.hide()
        self.info.show()
        self.progress_label.hide()
        self.progress.hide()

    def seeDetails(self):
        msgTxt = '\n'.join(self.flags)
        msgTxt = 'Potential issues encountered while reading example file:\n' + msgTxt
        dialogs.showWarning(self,msgTxt)
