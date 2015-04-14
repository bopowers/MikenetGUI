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

print 'Importing packages...'
from PySide import QtGui,QtCore
import lib.dialogs as dialogs
from lib.custom_widgets import CustomTabMaster
from lib.data_structures import MikenetScript,MikenetParameter
from lib.db_utils import pushRunData
import lib.io_utils as io
from lib.editor_windows import PreferencesEditor
import webbrowser
import tarfile
import os
import sys
import glob
import gzip
from shutil import rmtree
from time import sleep
from math import floor

class MainApp(QtGui.QMainWindow):
    '''Main application window is the top-level widget.'''
    def __init__(self,app,desktop_data):
        super(MainApp, self).__init__()
        self.app = app
        self.script = None
        self.main_tabs = None
        self.tab_registry = [] # for rapid updating of tabs
        self.parameters = {} # for storing preferences
        
        # get screen size
        self.w = desktop_data.width()
        self.h = desktop_data.height()
        
        self.initUI(self.w,self.h)
        
    def initUI(self,screen_width,screen_height):
        # create dummy central widget and main layout
        self.centralWidget = QtGui.QWidget()
        self.setCentralWidget(self.centralWidget)
        self.mainLayout = QtGui.QVBoxLayout()

        # display logo at top
        self.logo_layout = QtGui.QHBoxLayout()
        icon = QtGui.QPixmap(os.path.join(os.getcwd(),'resources',
                                                      'images','haskins_logo.png'))
        logo = QtGui.QLabel()
        logo.setPixmap(icon)
        self.logo_layout.addStretch(1)
        self.logo_layout.addWidget(logo)
        self.logo_layout.addStretch(1)
        self.mainLayout.addLayout(self.logo_layout)

        # create actions
        self.defineActions()

        # create menu bar
        self.setMenuBar(self.getMenu())

        # create a new script and its widget
        self.newScript()
        
        # putting it all together
        self.setWindowTitle('MikeNet GUI')
        icon = QtGui.QIcon(QtGui.QPixmap(os.path.join(os.getcwd(),'resources',
                                                      'images','icon_48x48.png')))
        self.setWindowIcon(icon)
        self.centralWidget.setLayout(self.mainLayout)

        self.setGeometry(100, 100, floor((screen_width*2)/3), floor((screen_height*2)/3))
        self.show()

    def getMainTabs(self):
        return self.main_tabs

    def getScript(self):
        return self.script
        
    def closeEvent(self,event):
        #reply = dialogs.saveOnCloseDialog(self)
        #if reply == QtGui.QMessageBox.Discard:
        #    event.accept()
        #elif reply == QtGui.QMessageBox.Save:
        #    event.accept()
        #else:
        #    event.ignore()
        pass

    def resetLayout(self):
        # create main tabbed viewing area
        if self.main_tabs:
            self.main_tabs.close()

        # reset tab registry
        self.tab_registry = []

    def newScript(self):
#        if self.script:
#            # ask to save first
#            ret_code = dialogs.saveOnNewDialog(self)
#            if ret_code == QtGui.QMessageBox.Save:
#                self.saveScript()
#            elif ret_code == QtGui.QMessageBox.Discard:
#                pass # don't save
#            else:
#                return # user cancelled
            
        self.resetLayout()
        self.script = MikenetScript(self)
        self.script.createNew()
        
        self.main_tabs = CustomTabMaster(self,self.script)
        self.main_tabs.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.mainLayout.addWidget(self.main_tabs)

    def openScript(self):
#        if self.script:
#            # ask to save first
#            ret_code = dialogs.saveOnNewDialog(self)
#            if ret_code == QtGui.QMessageBox.Save:
#                self.saveScript()
#            elif ret_code == QtGui.QMessageBox.Discard:
#                pass # don't save
#            else:
#                return # user cancelled
                
        fname = dialogs.openScript(self)
        if not fname:
            return

        self.resetLayout()
        
        self.script = io.readScript(self,fname)
        self.main_tabs = CustomTabMaster(self,self.script)
        self.main_tabs.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.mainLayout.addWidget(self.main_tabs)

        self.script.getTabWidget().refreshTabContents()
        

    def saveScript(self):
        fname = dialogs.saveScript(self)
        if fname:
            io.writeScript(self.script,fname)

    def showHelp(self):
        webbrowser.open(os.path.join(os.getcwd(),'doc','help.html'))

    def showAbout(self):
        dialogs.showAbout(self)

    def defineActions(self):
        self.exit_action = QtGui.QAction('Exit',self)        
        self.exit_action.setShortcut('Ctrl+Q')
        self.exit_action.triggered.connect(self.close)

        self.new_file_action = QtGui.QAction('New Script',self)
        self.new_file_action.setShortcut('Ctrl+N')
        self.new_file_action.triggered.connect(self.newScript)

        self.open_file_action = QtGui.QAction('Open Script',self)
        self.open_file_action.setShortcut('Ctrl+O')
        self.open_file_action.triggered.connect(self.openScript)

        self.save_file_action = QtGui.QAction('Save Script',self)
        self.save_file_action.setShortcut('Ctrl+S')
        self.save_file_action.triggered.connect(self.saveScript)

        self.prefs_action = QtGui.QAction('Edit Preferences',self)
        self.prefs_action.triggered.connect(self.editPreferences)

        self.dbupdate_action = QtGui.QAction('Update Database',self)
        self.dbupdate_action.triggered.connect(self.updateDatabase)
        self.dbupdate_action.setShortcut('Ctrl+U')
        
        self.help_action = QtGui.QAction(QtGui.QIcon(os.path.join(os.getcwd(),'resources',
                                                        'images','help.png')),'Help',self)
        self.help_action.setShortcut('Ctrl+H')
        self.help_action.triggered.connect(self.showHelp)

        self.about_action = QtGui.QAction('About',self)
        self.about_action.triggered.connect(self.showAbout)
    
    def getMenu(self):
        menubar = QtGui.QMenuBar()  
        fileMenu = menubar.addMenu('File')
        helpMenu = menubar.addMenu('Help')
    
        fileMenu.addAction(self.new_file_action)
        fileMenu.addAction(self.open_file_action)
        fileMenu.addAction(self.save_file_action)
        fileMenu.addSeparator()
        fileMenu.addAction(self.prefs_action)
        fileMenu.addAction(self.dbupdate_action)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exit_action)
        helpMenu.addAction(self.help_action)
        helpMenu.addSeparator()
        helpMenu.addAction(self.about_action)

        return menubar

    def registerTabbedObject(self,obj):
        self.tab_registry.append(obj)
        
    def unRegisterTabbedObject(self,obj):
        if obj in self.tab_registry:
            self.tab_registry.remove(obj)

    def updateAllTabs(self):
        '''To make sure data on distant tabs are updated without having to interact with them.

        Sometimes throws up errors when dealing with phase widgets, so that's why the try/catch
        blocks are used. The exceptions have been ignorable, so we won't care about them.'''
        # update phase items first
        subset = [x for x in self.tab_registry if
                  x.getClassName() == 'MikenetPhaseItem']
        for obj in subset:
            try:
                obj.getTabWidget().refreshTabContents()
            except:
                pass
        # then runs
        subset = [x for x in self.tab_registry if
                  x.getClassName() == 'MikenetRun']
        for obj in subset:
            try:
                obj.getTabWidget().refreshTabContents()
            except:
                pass
        # then iterators
        subset = [x for x in self.tab_registry if
                  x.getClassName() == 'MikenetIterator']
        for obj in subset:
            try:
                obj.getTabWidget().refreshTabContents()
            except:
                pass
        # finally the script tab
        subset = [x for x in self.tab_registry if
                  x.getClassName() == 'MikenetScript']
        for obj in subset:
            try:
                obj.getTabWidget().refreshTabContents()
            except:
                pass

    def getApp(self):
        return self.app
            
    def showBriefLicense(self):
        # spit GNU license information to console
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
    def editPreferences(self):
        ed = PreferencesEditor(self)
        ed.exec_()

    def savePreferences(self):
        try:
            with open(os.path.join(os.getcwd(),'resources','preferences'),'w') as f:
                f.write('<preferences>\n')
                f.write('\n')
                for p in self.parameters.values():
                    io.writeParameter(f,p,'\t')
                    f.write('\n')
                f.write('</preferences>\n')
                
        except IOError:
            dialogs.showWarning(self,'There was a problem writing to "resources/preferences". Process aborted.')

        # also write new mikenet_path to the SConstruct template file
        try:
            with open(os.path.join(os.getcwd(),"resources","template_code","SConstruct"),"r") as f:
                lines = f.readlines()
                new_path_line = None
                new_path_index = 0
                for i,line in enumerate(lines):
                    if "MIKENET_DIR =" in line:
                        # original line looks like MIKENET_DIR = blahblah;
                        if sys.platform == 'win32':
                            new_path_str = self.parameters['mikenet_path'].value.replace('\\','/')
                        else:
                            new_path_str = self.parameters['mikenet_path'].value
                            
                        new_path_line = str("MIKENET_DIR = os.path.normpath('" +
                                            new_path_str + "')\n")
                        new_path_index = i
                        break
                lines[new_path_index] = new_path_line

                with open(os.path.join(os.getcwd(),"resources","template_code","SConstruct"),"w") as f:
                    f.writelines(lines)
        except IOError:
            dialogs.showWarning(self,'There was a problem writing to the SCons template. Process aborted.')

    def loadPreferences(self):
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
                print '''ERROR: There was a problem reading "resources/preferences". Quitting.

Details:
The program attempted to restore backup (default) preferences, but failed.

You may need to reinstall the program to get the orginal preferences back.
'''
            self.destroy()
            sys.exit(1)

    def pushData(self,path,run_name,msg):
        print 'In pushData!'
        print path
        print run_name
        msg.setText('Updating database records for '+run_name+'\nThis could take a while...')
        for unzipthis in glob.iglob(os.path.join(path,'*.gz')):
            f_in = gzip.open(os.path.join(path,unzipthis),'rb')
            f_out = open(os.path.join(path,unzipthis[:-3]),'wb')
            f_out.writelines(f_in)
            f_in.close()
            f_out.close()
            os.remove(os.path.join(path,unzipthis))

        ret = pushRunData(path,self)
        if ret:
            # there was a problem
            print 'Warning: Could not update',run_name,'records in database.'
        for ex in ['*.activations','*.test','*.weights']:
            for zipthis in glob.iglob(os.path.join(path,ex)):
                print 'zipping',zipthis
                f_in = open(os.path.join(path,zipthis),'rb')
                f_out = gzip.open(os.path.join(path,(zipthis+'.gz')),'wb')
                f_out.writelines(f_in)
                f_out.close()
                f_in.close()
                os.remove(os.path.join(path,zipthis))
        
        return ret

    def updateDatabase(self):
        if self.parameters['use_database'].value == 1:
            msg = QtGui.QMessageBox(self)
            msg.setWindowTitle('Updating database')
            msg.setIcon(QtGui.QMessageBox.Information)
            msg.setText('Scanning MikenetGUI/data/* tree for unsaved data.')
            msg.show()
            msg.raise_()
            msg.activateWindow()
            for script_dir in os.listdir(os.path.join(os.getcwd(),'data')):
                if os.path.isdir(os.path.join(os.getcwd(),'data',script_dir)):
                    for run in os.listdir(os.path.join(os.getcwd(),'data',script_dir)):
                        runname = run
                        #debug
                        print runname
                        if '.gz' in runname:
                            runname = os.path.splitext(runname)[0]
                        if '.tar' in runname:
                            runname = os.path.splitext(runname)[0]
                            
                        if not os.path.isdir(os.path.join(os.getcwd(),'data',script_dir,run)) and \
                            tarfile.is_tarfile(os.path.join(os.getcwd(),'data',script_dir,run)):
                            #debug
                            print 'FLAG 1'
                            unpacking = False
                            # don't untar without a reason. look for db_flag inside the tar first
                            tar = tarfile.open(os.path.join(os.getcwd(),'data',script_dir,run),'r')
                            for member in tar.getmembers():
                                junk,mname = os.path.split(member.name)
                                if mname == 'db_flag':
                                    unpacking = True
                                    break
                            if unpacking:
                                #debug
                                print 'There is a db_flag!'
                                tar.extractall()
                                tar.close()
                                ret = self.pushData(os.path.join(os.getcwd(),runname),runname,msg)
                                if not ret:
                                    # this is the case where database push was successful
                                    # so delete the db_flag and retar
                                    os.remove(os.path.join(os.getcwd(),'data',script_dir,run))
                                    tar = tarfile.open(os.path.join(os.getcwd(),'data',script_dir,run),'w:gz')
                                    os.chdir(runname)
                                    for tf in os.listdir(os.getcwd()):
                                        if tf != 'db_flag':
                                            tar.add(tf)
                                    os.chdir(os.pardir)
                                rmtree(runname)
                            tar.close()
                        else:
                            print 'FLAG 2'
                            for member in os.listdir(os.path.join(os.getcwd(),'data',script_dir,run)):
                                if member == 'db_flag':
                                	ret = self.pushData(os.path.join(os.getcwd(),'data',script_dir,run),run,msg)
                                	if not ret:
                                		# remove the db_flag
                                		os.remove(os.path.join(os.getcwd(),'data',script_dir,run,'db_flag'))
                                	# now tar the whole thing
                                	tar = tarfile.open(os.path.join(os.getcwd(),'data',script_dir,str(run+'.tar.gz')),'w:gz')
                                	mainwd = os.getcwd()
                                	os.chdir(os.path.join(os.getcwd(),'data',script_dir,run))
                                	for tf in os.listdir(os.getcwd()):
                                		tar.add(tf)
                                	tar.close()
                                	os.chdir(mainwd)
                                	rmtree(os.path.join(os.getcwd(),'data',script_dir,run))
                                	break
            msg.setText('Database is up to date.')
        else:
            dialogs.showWarning(self,'No database is defined. Go to File->Edit Preferences to change this.') 

    def emailNotify(self,run_time):
        if self.parameters['email_notification'].value == 1:
            try:
                # what is most natural way to state the time?
                hours = str(str(int(floor(run_time/3600))) + ' hours')
                minutes = str(str(int(floor((run_time % 3600)/60))) + ' minutes')
                seconds = str(str(round((run_time % 3600) % 60)) + ' seconds')
                import smtplib
                from email.mime.text import MIMEText
                text = str('This is an automated notification from MikeNetGUI, informing you that\n' +
                       'script "' + self.getScript().getValueOf('script_name') + '" has completed running.\n' +
                       '\n' +
                       'Total execution time was ' + ': '.join([hours,minutes,seconds]) + '.\n\n\n' +
                       '(This message was generated automatically. Do not attempt to reply.)')
                
                msg = MIMEText(text)
                msg['Subject'] = 'MikeNetGUI automated message RE: %s' % self.getScript().getValueOf('script_name')
                msg['From'] = 'mikenetgui.auto.message@gmail.com'
                msg['To'] = self.parameters['email_address'].value
                # a temp gmail account was set up for this, but this can be changed if necessary
                s = smtplib.SMTP('smtp.gmail.com:587')
                s.starttls()
                s.login(msg['From'],'7xW.y39E')  
                s.sendmail(msg['From'], [msg['To']], msg.as_string())
                s.quit()
            except:
                dialogs.showWarning(self,str('Could not send email notification. \n' +
                                             'If problem recurs, disable email notifications \n' +
                                             'or update SMTP credentials in "gui.py".'))


def main(): 
        try: 
            app = QtGui.QApplication(sys.argv)
            
        except RuntimeError:
            app = QtCore.QCoreApplication.instance()

        splash_img = QtGui.QPixmap(os.path.join(os.getcwd(),'resources',
                                                'images','splash.png'))
        splash = QtGui.QSplashScreen(splash_img,QtCore.Qt.WindowStaysOnTopHint)
        splash.show()
        splash.raise_()
        # get info for determining main window size and position
        desktop_data = app.desktop()
        
        # initialize the gui
        gui = MainApp(app,desktop_data)
        app.processEvents()
        splash.raise_()

        # load preferences
        splash.showMessage('Loading preferences...')
        print 'Loading preferences...'
        app.processEvents()
        splash.raise_()
        gui.loadPreferences()

        gui.showBriefLicense()
        sleep(2) # extra time to show off awesome Powerpoint splash screen!
        splash.finish(gui)
        app.exec_()


if __name__ == '__main__':
    main()
