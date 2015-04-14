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
import gen_utils as guts
import dialogs
from editor_windows import OverrideEditor, LinkToTestEditor
from copy import deepcopy
import os

class CustomTabMaster(QtGui.QTabWidget):
    def __init__(self,gui,script):
        super(CustomTabMaster, self).__init__(gui)
        self.gui = gui
        self.script = script
        self.currentChanged.connect(self.refreshCurrent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.profile_edit_mode = False

        # add corner widget, always visible
        self.setCornerWidget(CustomTabCornerWidget(self))

        # individual tabs can't be hidden, so keep widgets
        # alive by having them attached to their data objects.
        # this works because there is a one-to-one relationship
        # between tree objects (script, run, etc) and tabs

        # show script tab which will always be visible
        self.addTab(script.getTabWidget(),
                    str('Script: '+script.getValueOf('script_name')))

    def requestTab(self,data_object):
        if data_object:
            level = data_object.getTabWidget().getLevel()
        else:
            level = 0
        
        # iterate over tabs (excluding first and last)
        # if level >= the tab's level, remove that tab
        removals = []
        for i in range(1,self.count()):
            widget = self.widget(i)
            if widget.getLevel() >= level:
                removals.append(i)
        for i in reversed(removals):
            self.removeTab(i)
        # finally, add the tab for the widget you want to show
        self.showWidgetTab(data_object)

    def showWidgetTab(self,data_object):
        self.addTab(data_object.getTabWidget(),
                       data_object.getTabWidget().getTabName())
    
    def removeTabByObject(self,data_object):
        for i in range(self.count()):
            if self.tabText(i) == data_object.getTabWidget().getTabName():
                self.removeTab(i)
                break

    def switchCurrentTab(self,data_object):
        for i in range(self.count()):
            if self.tabText(i) == data_object.getTabWidget().getTabName():
                self.setCurrentIndex(i)
                break

    def refreshCurrent(self,i):
        # if you have been in profile edit mode, get rid of profile tab
        if self.profile_edit_mode:
            if i == 1:
                return
            else:
                self.removeTab(1)
                self.profile_edit_mode = False

        self.widget(i).refreshTabContents()
        self.setTabText(i,self.widget(i).getTabName())

    def refreshTabNames(self):
        for i in range(self.count()):
            self.setTabText(i,self.widget(i).getTabName())

    def profileEditorRequested(self):
        # remove every tab except the script tab
        for i in reversed(range(1,self.count())):
            self.removeTab(i)
        self.addTab(self.script.getProfilesTabWidget(),'Train/Test Sets')
        self.profile_edit_mode = True
        self.setCurrentIndex(1)
        

class CustomTabCornerWidget(QtGui.QPushButton):
    def __init__(self,parent):
        super(CustomTabCornerWidget, self).__init__('Edit Train/Test Sets')
        #self.setStyleSheet('border: 1px solid black')
        self.main_tabs = parent
        self.clicked.connect(self.clickedButton)

    def sizeHint(self):
        return QtCore.QSize(self.fontMetrics().width('xxEdit Train/Test Setsxx'),
                            2*self.fontMetrics().height())

    def clickedButton(self):
        self.main_tabs.profileEditorRequested()

class CustomListWidget(QtGui.QListWidget):
    '''Custom list widget allowing multiple lines and draggable ordering.
    '''
    def __init__(self,parent,level_root):
        '''Parent is the tab widget containing this component.

        Level-root is the data object corresponding to the parent tab.

        '''
        super(CustomListWidget, self).__init__(parent)
        self.parent = parent
        self.level_root = level_root
        self.current_object = None
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)

        self.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.createLinePalette()

    def syncToModel(self):
        self.clear()
        for child in self.level_root.getChildren():
            if child is self.current_object:
                isSel = True
            else:
                isSel = False
            for text in child.getDisplayLines():
                self.addItem(CustomListLine(child,text,isSel))
        self.colorLines()
        self.parent.updateProfileInfo(self.current_object)

    def createLinePalette(self):
        # line background colors
        self.color_select_bg = QtGui.QColor(152,245,255)
        self.color_run_txt = QtGui.QColor(255,0,0)
        self.color_iter_txt = QtGui.QColor(0,0,255)
        self.color_profile_txt = QtGui.QColor(85,26,139)
        self.color1 = QtGui.QColor(255,255,255)
        self.color2 = QtGui.QColor(240,240,240)
        self.color_white = QtGui.QColor(255,255,255)
        self.color_black = QtGui.QColor(0,0,0)

    def colorLines(self):
        obj = None
        c = 0
        for i in range(self.count()):
            line_widget = self.item(i)
            # background color
            if line_widget.isSelected():
                # special selection color
                line_widget.setBackground(self.color_select_bg)
                # still keep track of object for counting purposes
                if line_widget.getDataObject() is obj:
                    pass
                else:
                    obj = line_widget.getDataObject()
                    c += 1
            else:
                # alternate between the 2 background colors for easier visual separation
                if line_widget.getDataObject() is obj:
                    pass
                else:
                    obj = line_widget.getDataObject()
                    c += 1
                if c % 2 == 0:
                    line_widget.setBackground(self.color2)
                else:
                    line_widget.setBackground(self.color1)
                    
            # text color
            if 'Run>' in line_widget.text():
                line_widget.setForeground(self.color_run_txt)
            elif 'Iterator>' in line_widget.text():
                line_widget.setForeground(self.color_iter_txt)
            elif 'Training Set>' in line_widget.text():
                line_widget.setForeground(self.color_profile_txt)
            elif 'Test Set>' in line_widget.text():
                line_widget.setForeground(self.color_profile_txt)
            else:
                line_widget.setForeground(self.color_black)

    def addDataObject(self):
        self.insertDataObject(len(self.level_root.getChildren())+1)

    def insertDataObject(self,index):
        root = self.level_root.getClassName()
        if root == 'MikenetRun':
            self.level_root.insertPhase(index)
        elif root == 'MikenetPhase':
            pass
        self.syncToModel()

    def removeCurrentObject(self):
        if self.current_object:
            self.current_object.parent.removeChild(self.current_object)
            self.syncToModel()
        
    def getCurrentObject(self):
        return self.current_object

    def mousePressEvent(self,event):
        xyLoc = event.pos()
        widget = self.itemAt(xyLoc)
        if not widget:
            self.current_object = None
            self.syncToModel()
            return
        self.current_object = widget.getDataObject()
        index = self.level_root.getChildren().index(self.current_object)
        self.syncToModel()
        
        # mouse dragging stuff    
        itemData = QtCore.QByteArray()
        dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
        dataStream << QtCore.QByteArray(str(index))
        mimeData = QtCore.QMimeData()
        mimeData.setData('application/x-listLine', itemData)
        self.drag = QtGui.QDrag(self.parent)
        self.drag.setMimeData(mimeData)
        self.drag.exec_()


    def mouseDoubleClickEvent(self,event):
        if self.level_root.getClassName() == 'MikenetProfileCollection':
            # this does not have a tab associated with it
            self.parent.editProfile()
        else:
            # open and view the double clicked item's tab
            self.level_root.getGUI().getMainTabs().requestTab(self.current_object)
            self.level_root.getGUI().getMainTabs().switchCurrentTab(self.current_object)
            

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-listLine'):
            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.ignore()

    def dropEvent(self, event):       
        if event.mimeData().hasFormat('application/x-listLine'):
            mime = event.mimeData()
            itemData = mime.data('application/x-listLine')
            dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.ReadOnly)
            
            text = QtCore.QByteArray()
            offset = QtCore.QPoint()
            dataStream >> text
            
            try:
                # Python v3.
                text = str(text, encoding='latin1')
            except TypeError:
                # Python v2.
                text = str(text)

            self.handleDrop(text,event)
                            
            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.ignore()         

    dragMoveEvent = dragEnterEvent

    def handleDrop(self,text,event):
        '''Subclass and override this method to do widget-specific things.'''
        # what index did we drag to?
        xyLoc = event.pos()
        widget = self.itemAt(xyLoc)
        if not widget:
            event.ignore()
            return
        destinationObj = widget.getDataObject()
        to_index = self.level_root.getChildren().index(destinationObj)
        from_index = int(text)
        # reorder
        guts.moveInPlace(self.level_root.getChildren(),from_index,to_index)
        self.syncToModel()


class CustomTreeWidget(CustomListWidget):
    '''Reimplementation of CustomListWidget. Allows hierarchical embeds.
    '''
    def __init__(self,parent,level_root):
        super(CustomTreeWidget, self).__init__(parent,level_root)

    def syncToModel(self):
        self.clear()
        self.DFSDisplay(self.level_root,0)
        self.colorLines()

    def syncToTabs(self):
        gui = self.level_root.getGUI()
        gui.getMainTabs().requestTab(self.current_object)
        
    def newRun(self):
        # are we adding or inserting? depends on if there is current selected object
        if self.current_object:
            # get parent and index for insertion
            if self.current_object.getClassName() == 'MikenetIterator':
                if self.current_object.getMyRun():
                    # iterator is selected, but it already has a run
                    # so append to the end of the script
                    self.level_root.getChildren().append(self.level_root.makeNewRun(self.level_root))
                else:
                    # iterator is selected, with no runs inside
                    # so add the run as the iterator's child (as low in tree as possible)
                    traceNode = self.current_object
                    while traceNode.getChildren():
                        traceNode = traceNode.getChildren()[0]
                    parent = traceNode
                    parent.getChildren().append(self.level_root.makeNewRun(parent))
            else:
                # run is currently selected, so insert right after selected run IF
                # the run is not embedded in an iterator...in that case, append it
                # to end of script
                if self.current_object.parent.getClassName() == 'MikenetIterator':
                    # append to end
                    self.level_root.getChildren().append(self.level_root.makeNewRun(self.level_root))
                else:
                    parent = self.current_object.parent
                    index = parent.getChildren().index(self.current_object)
                    # make a new run and insert it
                    parent.getChildren().insert(index+1,self.level_root.makeNewRun(parent))
        else:
            # use append instead of insert...make a direct descendent of script
            self.level_root.getChildren().append(self.level_root.makeNewRun(self.level_root))
        self.syncToModel()
    
    def newIterator(self):
        # are we adding or inserting? depends on if there is current selected object
        if self.current_object:
            # get parent and index for insertion
            if self.current_object.getClassName() == 'MikenetIterator':
                new_it = self.level_root.makeNewIterator(self.current_object)
                if self.current_object.getChildren():
                    # insert the new iterator between the parent and whatever it's other children were
                    original_child = self.current_object.getChildren().pop(0)
                    original_child.parent = new_it
                    new_it.getChildren().append(original_child)
                    self.current_object.getChildren().append(new_it)
                else:
                    # nothing in this iterator, so you can add
                    self.current_object.getChildren().append(new_it)
            else:
                # run is currently selected, so insert right after selected run IF
                # the run is not embedded in an iterator...in that case, append it
                # to end of script
                if self.current_object.parent.getClassName() == 'MikenetIterator':
                    # append to end
                    self.level_root.getChildren().append(self.level_root.makeNewIterator(self.level_root))
                else:
                    parent = self.current_object.parent
                    index = parent.getChildren().index(self.current_object)
                    # make a new run and insert it
                    parent.getChildren().insert(index+1,self.level_root.makeNewIterator(parent))
        else:
            # use append instead of insert...make a direct descendent of script
            self.level_root.getChildren().append(self.level_root.makeNewIterator(self.level_root))
        self.syncToModel()

    def removeCurrentObject(self):
        if self.current_object:
            # unregister tab and ALL descendent tabs from GUI
            self.current_object.getGUI().unRegisterTabbedObject(self.current_object)
            guts.DFS_deTab(self.current_object)
            # remove the tab from the main tabs view
            self.level_root.getGUI().getMainTabs().removeTabByObject(self.current_object)
            # destroy tab
            self.current_object.getTabWidget().destroy()
            # remove data node from the tree
            self.current_object.parent.removeChild(self.current_object)
            self.current_object = None
            # now since current is None, disable buttons that require selected object
            self.parent.del_btn.setEnabled(False)
            self.parent.dup_btn.setEnabled(False)
            # finally update the tab to reflect underlying data
            self.syncToModel()
            
    def duplicateCurrentObject(self):
        if self.current_object:
            if self.current_object.getClassName() == 'MikenetRun':
                the_copy = self.current_object.getCopy()
                the_copy.getParameter('run_name').value = str(self.current_object.getValueOf('run_name') +
                                                              ' - COPY')
                the_copy.createTab()
                the_copy.tabifyChildren() # recursively creates tabs
                
            elif self.current_object.getClassName() == 'MikenetIterator':
                the_copy = self.current_object.getCopy()
                the_copy.getParameter('iterator_name').value = str(self.current_object.getValueOf('iterator_name') +
                                                                    ' - COPY')
                the_copy.createTab()
                the_copy.tabifyChildren()

            # always put run copy at the top level, but insert it right after the original
            # to find branch of the original run, trace back up to the root
            traceNode = self.current_object
            index = 0
            while traceNode.parent:
                index = traceNode.parent.getChildren().index(traceNode)
                traceNode = traceNode.parent
                
            self.level_root.getChildren().insert(index+1,the_copy)
            # manually set parent
            the_copy.parent = self.level_root
                
        self.syncToModel()

    def getNewRunNames(self):
        names = []
        for i in range(self.count()):
            line_widget = self.item(i)
            if 'Name:' in line_widget.text() and 'newRun' in line_widget.text():
                l,r = line_widget.text().split('Name: ')
                names.append(r)

        return names

    def getIteratorNames(self):
        names = []
        for i in range(self.count()):
            line_widget = self.item(i)
            if 'Name:' in line_widget.text() and 'newIterator' in line_widget.text():
                l,r = line_widget.text().split('Name: ')
                names.append(r)

        return names

    def DFSDisplay(self,node,depth):
        for child in node.getChildren():
            if child.getClassName() == 'MikenetIterator':
                child.syncToRun()
                # is this currently selected?
                if child is self.current_object:
                    isSel = True
                else:
                    isSel = False
                # add this iterator to display
                space = ' '*10*depth
                self.addItem(CustomListLine(child,
                                            space+'<Iterator>',
                                            isSel))
                for text in child.getDisplayLines():
                    self.addItem(CustomListLine(child,
                                            space+text,
                                            isSel))
                self.DFSDisplay(child,depth+1)
                self.addItem(CustomListLine(child,
                                            space+'',
                                            isSel))
                self.addItem(CustomListLine(child,
                                            space+'</Iterator>',
                                            isSel))
            else:
                # is this currently selected?
                if child is self.current_object:
                    isSel = True
                else:
                    isSel = False
                # add this run
                space = ' '*10*depth
                for text in child.getDisplayLines():
                    self.addItem(CustomListLine(child,
                                            space+text,
                                            isSel))

    def mousePressEvent(self,event):
        xyLoc = event.pos()
        widget = self.itemAt(xyLoc)
        if not widget:
            self.current_object = None
            self.parent.del_btn.setEnabled(False)
            self.parent.dup_btn.setEnabled(False)
            self.syncToModel()
            return
        self.current_object = widget.getDataObject()
        self.parent.del_btn.setEnabled(True)
        self.parent.dup_btn.setEnabled(True)
        
        self.syncToModel()
        self.syncToTabs()

        traceNode = widget.getDataObject()
        traversal_string = str(self.getTraversalList(traceNode))
 
        itemData = QtCore.QByteArray()
        dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
        dataStream << QtCore.QByteArray(traversal_string)
        mimeData = QtCore.QMimeData()
        mimeData.setData('application/x-listLine', itemData)
        self.drag = QtGui.QDrag(self)
        self.drag.setMimeData(mimeData)

        if self.drag.exec_(QtCore.Qt.MoveAction | QtCore.Qt.CopyAction,
                           QtCore.Qt.CopyAction) == QtCore.Qt.MoveAction:
            pass
        else:
            pass

    def getTraversalList(self,traceNode):
        ## get data to store in drag
        # data stream contains string with info about position in tree
        # string format will be a string representation of a list
        # where the depth increases with each element in the list
        searchingTree = True
        treePosList = []
        while searchingTree:
            if traceNode.parent:
                # parent must be an iterator, get my child position
                i = traceNode.parent.children.index(traceNode)
                treePosList.append(i)
                traceNode = traceNode.parent # repeat with parent
            else:
                searchingTree = False
                break
            
        treePosList.reverse()
        return treePosList

    def unpackDragDataObject(self,data):
        # data will be a list of integer child indices,
        # each representing a deeper level in the tree
        node = self.level_root
        for index in eval(data):
            node = node.getChildren()[int(index)]  
        return node

    def doTreeSurgery(self,sub_root_obj,make_child_of_obj):
        siblings = sub_root_obj.parent.getChildren()
        removed_node = siblings.pop(siblings.index(sub_root_obj))
        make_child_of_obj.getChildren().append(removed_node)
        removed_node.parent = make_child_of_obj
            

    def handleDrop(self,text,event):
        '''SORRY, this is confusing as hell.'''
        # what index did we drag to?
        xyLoc = event.pos()
        to_widget = self.itemAt(xyLoc)
        fromObj = self.unpackDragDataObject(text)
        if to_widget:
            # first, if you dragged something into itself, ignore
            destinationObj = to_widget.getDataObject()
            if fromObj is destinationObj:
                event.ignore()
                return
            # second, check if you have dragged a parent widget into
            # its offspring. this is also not allowed
            traceNode = destinationObj
            while traceNode.parent:
                if traceNode.parent is fromObj:
                    event.ignore()
                    return
                else:
                    traceNode = traceNode.parent
            # behavior determined by what widget type was dragged,
            # and what type it was dragged into
            if destinationObj.getClassName() == 'MikenetRun':
                if destinationObj.parent.getClassName() == 'MikenetIterator':
                    # destination was an embedded run
                    if fromObj.getClassName() == 'MikenetRun':
                        # CAN'T drag another run here
                        # ignore the drag. display warning.
                        dialogs.showWarning(self,'Iterator already contains an embedded run.')
                        event.ignore()
                        return
                    else:
                        # can possibly drag an iterator here, but only if it has no run already
                        # check to see if the dragged iterator has a run
                        if fromObj.getMyRun():
                            # ignore the drag
                            event.ignore()
                            return
                        else:
                            parent_iter = destinationObj.parent
                            self.doTreeSurgery(destinationObj,fromObj) # make run child of iter
                            self.doTreeSurgery(fromObj,parent_iter) # make iter child of larger iter
                            # now tree should be reconnected with the dragged iterator sandwiched one-
                            # level above the run it was dragged into
                else:
                    # destination was a NON embedded (script-level) run
                    # reconnect the dragged subtree
                    # same as tree surgery but inserting instead of appending
                    siblings = fromObj.parent.getChildren()
                    removed_node = siblings.pop(siblings.index(fromObj))
                    destIndex = self.level_root.getChildren().index(destinationObj)
                    self.level_root.getChildren().insert(destIndex,removed_node)
                    removed_node.parent = self.level_root
            else:
                if fromObj.getClassName() == 'MikenetIterator':
                    # dragging an iterator into an iterator. same logic as dragging iterator into
                    # embedded run
                    if destinationObj.getMyRun():
                        # target iterator already has a run. check the dragged iterator
                        if fromObj.getMyRun():
                            # ignore the drag
                            event.ignore()
                            return
                        else:
                            parent_iter = destinationObj
                            self.doTreeSurgery(destinationObj.getMyRun(),fromObj) # make run child of iter
                            self.doTreeSurgery(fromObj,parent_iter) # make iter child of target iter

                    else:
                        # target has no run, so just connect the dragged iterator to it
                        self.doTreeSurgery(fromObj,destinationObj)
                else:
                    # dragging a run into an iterator..make sure the iterator has no run already
                    if destinationObj.getMyRun():
                        # CAN'T drag another run here
                        # ignore the drag. display warning.
                        dialogs.showWarning(self,'Iterator already contains an embedded run.')
                        event.ignore()
                        return
                    else:
                        # follow nodes down to insert as low in the tree as possible
                        traceNode = destinationObj
                        while traceNode.getChildren():
                            traceNode = traceNode.getChildren()[0]
                        self.doTreeSurgery(fromObj,traceNode)
        else:
            # simply append the object to the end of the top level
            self.doTreeSurgery(fromObj,self.level_root)
            
        self.syncToModel()


class CustomListLine(QtGui.QListWidgetItem):
    def __init__(self,node,text,isSel):
        super(CustomListLine,self).__init__(text,None,0)
        self.myNode = node
        self.selected = isSel
        # set flags to allow drops and override single line selection
        self.setFlags(QtCore.Qt.ItemIsDropEnabled)
        font = QtGui.QFont()
        font.setWeight(QtGui.QFont.Bold)
        self.setFont(font)

    def getDataObject(self):
        return self.myNode

    def isSelected(self):
        return self.selected
    
    
class CustomWiringWidget(QtGui.QTableWidget):
    '''Doc here
    '''
    def __init__(self,parent,run):
        super(CustomWiringWidget, self).__init__(parent)
        self.parent = parent
        self.run = run
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.cellClicked.connect(self.clickHandler)

        self.current_group = None

        # initialize
        self.syncToRun()

    def setCurrentGroup(self,i):
        self.current_group = i
        # tell the tab that this group has been clicked
        self.run.getTabWidget().updateGroupInfo(self.current_group)
        
    def syncToRun(self):
        self.clear()
        self.setRowCount(len(self.run.getGroups())+2)
        self.setColumnCount(len(self.run.getGroups())+1)
        self.updateGroupLabels()
        self.updateConnectionMatrix()

    def updateGroupLabels(self):
        for r in range(1,self.rowCount()-1):
            name = self.run.getGroups()[r-1]['name']
            if self.current_group == r-1:
                isSel = True
            else:
                isSel = False
            self.setCellWidget(r,0,CustomGroupTextCell(self,name,r-1,isSel))
        self.setCellWidget(self.rowCount()-1,0,
                           CustomGroupTextCell(self,"Bias",r-1,False))

        for c in range(1,self.columnCount()):
            name = self.run.getGroups()[c-1]['name']
            if self.current_group == c-1:
                isSel = True
            else:
                isSel = False
            self.setCellWidget(0,c,CustomGroupTextCell(self,name,c-1,isSel))

    def updateConnectionMatrix(self):
        matrix = self.run.getMatrix()
        self.setCellWidget(0,0,CustomConnectionCell(self,'off',None,None))
        for r in range(1,self.rowCount()):
            for c in range(1,self.columnCount()):
                if matrix[r-1][c-1] == 1:
                    state = 'on'
                else:
                    state = 'off'
                if r == self.rowCount()-1:
                    state = str('bias_'+state)
                if r == self.rowCount()-1:
                    g_f = 'Bias'
                else:
                    g_f = self.run.getGroups()[r-1]['name']
                g_t = self.run.getGroups()[c-1]['name']
                self.setCellWidget(r,c,CustomConnectionCell(self,
                                                            state,
                                                            g_f,g_t))

    def clickHandler(self,i,j):
        if i == j == 0:
            self.setCurrentGroup(None)
            self.syncToRun()
            return
        elif i == 0 or j == 0:
            pass # drag behavior
        else:
            self.toggleState(i,j)
        
    def toggleState(self,i,j):
        i -= 1
        j -= 1
        if self.run.getMatrix()[i][j] == 0:
            self.run.setConnection(i,j,1)
        else:
            self.run.setConnection(i,j,0)
        self.setCurrentGroup(None)
        self.syncToRun()                    

    def newGroup(self):
        # how many 'newGroup's are there already?
        existing = [x['name'] for x in self.run.getGroups()
                    if 'newGroup' in x['name']]
        self.run.newGroup(guts.getUnusedName('newGroup',existing))
        self.syncToRun()

    def deleteGroup(self):
        if self.current_group is not None:
            self.run.deleteGroup(self.current_group)
        self.setCurrentGroup(None)
        self.run.getGUI().updateAllTabs()

    def setGroupProperty(self,prop,value):
        if self.current_group is not None:
            group = self.run.getGroups()[self.current_group]
            # if changing name, make sure all children know about the change
            if prop == 'name':
                old_name = group[prop]
                self.trickleDownNameChange(old_name,value)
            group[prop] = value
            self.syncToRun()
            
    def trickleDownNameChange(self,old,new):
        for phase in self.run.getChildren():
            for phase_item in phase.getChildren():
                # net components first
                new_gc = list(phase_item.getComponentGroups())
                for i,g_name in enumerate(phase_item.getComponentGroups()):
                    if g_name == old:
                        new_gc[i] = str(new)
                        break
                phase_item.net_components['groups'] = new_gc
                new_cc = list(phase_item.getComponentConnections())
                for i,conn in enumerate(phase_item.getComponentConnections()):
                    g_from,g_to = conn.split('%')
                    if g_from == g_to == old:
                        new_cc[i] = str(new) + '%' + str(new)
                    elif g_from == old:
                        new_cc[i] = str(new) + '%' + g_to
                    elif g_to == old:
                        new_cc[i] = g_from + '%' + str(new)
                phase_item.net_components['connections'] = new_cc
                # now recording data
                phase_item.swapRecordingEntry(old,new)

    def dragEnterEvent(self,e):
        e.accept()
        
    dragMoveEvent = dragEnterEvent

class CustomComponentSelectionWidget(QtGui.QTableWidget):
    '''Doc here
    '''
    def __init__(self,parent,phase_item):
        super(CustomComponentSelectionWidget, self).__init__(parent)
        self.parent = parent
        self.phase_item = phase_item
        self.run = phase_item.parent.parent
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.cellClicked.connect(self.clickHandler)

        # initialize
        self.syncToRun()
        
    def syncToRun(self):
        # update record in data structure in case groups were renamed or removed
        group_names = [x['name'] for x in self.run.getGroups()]
        for group in self.phase_item.getComponentGroups():
            if group not in group_names:
                self.phase_item.removeGroupComponent(group)
        for conn in self.phase_item.getComponentConnections():
            g_from,g_to = conn.split('%')
            if (g_from not in group_names) or (g_to not in group_names):
                self.phase_item.removeConnectionComponent(conn)
        
        self.clear()
        self.setRowCount(len(self.run.getGroups())+1)
        self.setColumnCount(len(self.run.getGroups())+1)
        self.updateGroupLabels()
        self.updateConnectionMatrix()

    def updateGroupLabels(self):
        g_incl = self.phase_item.getComponentGroups()

        for r in range(1,self.rowCount()):
            name = self.run.getGroups()[r-1]['name']
            if name in g_incl:
                isIncl = True
            else:
                isIncl = False
            self.setCellWidget(r,0,CustomComponentGroupCell(self,name,r-1,isIncl))

        for c in range(1,self.columnCount()):
            name = self.run.getGroups()[c-1]['name']
            if name in g_incl:
                isIncl = True
            else:
                isIncl = False

            self.setCellWidget(0,c,CustomComponentGroupCell(self,name,c-1,isIncl))

    def updateConnectionMatrix(self):
        matrix = self.phase_item.getComponentMatrix()
        self.setCellWidget(0,0,CustomConnectionCell(self,'off',None,None))
        for r in range(1,self.rowCount()):
            for c in range(1,self.columnCount()):
                if matrix[r-1][c-1] == 0:
                    state = 'dead'
                elif matrix[r-1][c-1] == 1:
                    state = 'excluded'
                elif matrix[r-1][c-1] == 2:
                    state = 'included'

                g_f = self.run.getGroups()[r-1]['name']
                g_t = self.run.getGroups()[c-1]['name']
                
                self.setCellWidget(r,c,CustomConnectionCell(self,
                                                            state,
                                                            g_f,g_t))

    def clickHandler(self,i,j):
        if i == j == 0:
            pass # do nothing
        elif i == 0 or j == 0:
            pass # do nothing
        else:
            self.toggleConnection(i,j)
        
    def toggleConnection(self,i,j):
        if self.cellWidget(i,j).getState() == 'dead':
            return
        
        i -= 1
        j -= 1
        self.phase_item.toggleComponentConnection(i,j)
        self.syncToRun()
        # since noise controls are dependent on which components are included, 
        # let the tab know to update noise control widgets
        self.parent.updateNoiseControls()

    def toggleGroup(self,i):
        self.phase_item.toggleComponentGroup(i)
        # since so many things are dependent on which components are included,
        # update all tabs
        self.phase_item.getGUI().updateAllTabs()


class CustomPhaseWidget(QtGui.QTableWidget):
    '''Doc here
    '''
    def __init__(self,parent,run):
        super(CustomPhaseWidget, self).__init__(parent)
        self.parent = parent
        self.run = run
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        self.current_phase = 0

        # initialize
        self.syncToRun()

    def setCurrentIndex(self,i):
        self.current_phase = i
        # tell the tab that this phase has been clicked
        self.run.getTabWidget().updatePhaseInfo(self.current_phase,
                                            self.run.getChildren()[i].getValueOf('phase_name'))
        
    def syncToRun(self):
        self.clear()
        self.setRowCount(len(self.run.getChildren()))
        self.setColumnCount(4)
        self.setHorizontalHeaderLabels(['','Phase name','Order','Max Iterations'])
        self.setColumnWidth(0,self.fontMetrics().width('000'))
        self.updatePhaseData()

    def updatePhaseData(self):
        if self.run.getChildren():
            # NOTE: this line is in a try/catch block because it chokes when copying
            # this was a quick fix. should be ok because initially it isn't necessary
            try:
                self.run.getTabWidget().updatePhaseInfo(self.current_phase,
                            self.run.getChildren()[self.current_phase].getValueOf('phase_name'))
            except:
                pass
        for i,ph in enumerate(self.run.getChildren()):
            order = ph.getParameter('phase_order').getWidget()[1]
            order.currentIndexChanged.connect(self.syncToRun)
            if self.run.getTabWidget():
                order.currentIndexChanged.connect(self.run.getTabWidget().refreshChildPhaseWidgets)
            if i == self.current_phase:
                isSel = True
            else:
                isSel = False
            self.setCellWidget(i,0,CustomFixedTextCell(self,
                                str(i+1),self.run.getChildren(),i,isSel))
            self.setCellWidget(i,1,CustomFixedTextCell(self,
                                ph.getValueOf('phase_name'),self.run.getChildren(),i,isSel))
            self.setCellWidget(i,2,order)
            max_iter = ph.getParameter('max_iterations').getWidget()[1]
            self.setCellWidget(i,3,max_iter)
            if ph.getValueOf('phase_order') == 0:
                max_iter.setEnabled(False)
        self.resizeColumnToContents(1)

    def nameEditMode(self,edit_index):
        '''Like updatePhaseData() except it puts a specified label in edit mode.'''
        
        if self.run.getChildren():
            self.run.getTabWidget().updatePhaseInfo(self.current_phase,
                            self.run.getChildren()[self.current_phase].getValueOf('phase_name'))
        for i,ph in enumerate(self.run.getChildren()):
            order = ph.getParameter('phase_order').getWidget()[1]
            if i == self.current_phase:
                isSel = True
            else:
                isSel = False
            
            self.setCellWidget(i,0,CustomFixedTextCell(self,
                                str(i+1),self.run.getChildren(),i,isSel))
            if i == edit_index:
                name = ph.getParameter('phase_name').getWidget()[1]
                name.editingFinished.connect(self.updatePhaseData)
                self.setCellWidget(i,1,name)
            else:
                self.setCellWidget(i,1,CustomFixedTextCell(self,
                                ph.getValueOf('phase_name'),self.run.getChildren(),i,isSel))
            self.setCellWidget(i,2,order)

    def addPhase(self):
        self.run.newPhase()
        self.setCurrentIndex(len(self.run.getChildren())-1)
        self.syncToRun()

    def duplicatePhase(self):
        phase = self.run.getChildren()[self.current_phase]
        phase_copy = phase.getCopy()
        phase_copy.getParameter('phase_name').value = str(phase.getValueOf('phase_name') +
                                                          ' - COPY')
        phase_copy.parent = self.run
        self.run.getChildren().append(phase_copy)
        phase_copy.createWidget()
        phase_copy.tabifyChildren()
        self.syncToRun()

    def deletePhase(self):
        if len(self.run.getChildren()) == 1:
            dialogs.showWarning(self,'Run must have at least one phase.')
            return
        if self.current_phase is not None:
            self.run.deletePhase(self.current_phase)
        self.setCurrentIndex(0)
        self.syncToRun()
        self.run.getGUI().updateAllTabs()

    def setPhaseProperty(self,prop,value):
        if self.current_phase is not None:
            phase = self.getChildren()[self.current_phase]
            phase.parameters[prop] = value
            self.syncToRun()

    def dragEnterEvent(self,e):
        e.accept()

class CustomPhaseItemWidget(QtGui.QTableWidget):
    '''Doc here
    '''
    def __init__(self,parent,phase):
        super(CustomPhaseItemWidget, self).__init__(parent)
        self.parent = parent
        self.phase = phase
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)

        self.current_item = None

        # initialize
        self.syncToPhase()

    def setCurrentIndex(self,i):
        self.current_item = i
        # tell the tab that this set has been clicked
        self.phase.parent.getTabWidget().updatePhaseItemInfo(self.current_item)

    def mousePressEvent(self,event):
        # this means that user clicked on emptiness, set tab accordingly
        self.setCurrentIndex(None)
        self.updatePhaseItemData()

    def getCurrentIndex(self):
        return self.current_item    
              
    def syncToPhase(self):
        self.clear()
        self.setRowCount(len(self.phase.getChildren()))
        if self.phase.getValueOf('phase_order') == 0:
            self.setColumnCount(3)
            self.setHorizontalHeaderLabels(['','Set','Train/test'])
        else:
            self.setColumnCount(4)
            self.setHorizontalHeaderLabels(['','Set','Train/test','p'])
        self.setColumnWidth(0,self.fontMetrics().width('000'))
        self.updatePhaseItemData()

    def updatePhaseItemData(self):
        for i,pset in enumerate(self.phase.getChildren()):
            name = pset.getValueOf('item_name')
            mode = pset.getMode()
            if not self.current_item is None and i == self.current_item:
                isSel = True
            else:
                isSel = False
            self.setCellWidget(i,0,CustomFixedTextCell(self,
                                str(i+1),self.phase.getChildren(),i,isSel))
            self.setCellWidget(i,1,CustomFixedTextCell(self,
                                name,self.phase.getChildren(),i,isSel))
            self.setCellWidget(i,2,CustomFixedTextCell(self,
                                mode,self.phase.getChildren(),i,isSel))

            if self.phase.getValueOf('phase_order') == 1:
                self.setCellWidget(i,3,CustomFixedTextCell(self,
                                str(pset.getValueOf('probability')),
                                self.phase.getChildren(),i,isSel))

    def dragEnterEvent(self,e):
        e.accept()
        

class CustomGroupTextCell(QtGui.QLabel):
    def __init__(self,parent,text,group_index,sel):
        super(CustomGroupTextCell, self).__init__(parent)
        self.parent = parent
        self.group_index = group_index
        
        self.setText(text)
        self.setAlignment(QtCore.Qt.AlignRight)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.paintBackground(sel)
        
    def paintBackground(self,sel):
        if sel:
            self.setStyleSheet("background-color: rgb(152,245,255)")
        else:
            self.setStyleSheet("background-color: white")

    def mousePressEvent(self,event):
        if self.text() == 'Bias':
            return
        # tell the wiring widget that this is current so it can be highlighted
        self.parent.setCurrentGroup(self.group_index)
        # mouse dragging stuff    
        itemData = QtCore.QByteArray()
        dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
        dataStream << QtCore.QByteArray(str(self.group_index))
        mimeData = QtCore.QMimeData()
        mimeData.setData('application/x-groupLabel', itemData)
        self.drag = QtGui.QDrag(self.parent)
        self.drag.setMimeData(mimeData)
        self.drag.exec_()


    def mouseMoveEvent(self,event):
        self.parent.parent.setHelperText(str('Group: ' + self.text()))

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-groupLabel'):
            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):   
        if event.mimeData().hasFormat('application/x-groupLabel'):
            # unpack the drag data
            mime = event.mimeData()
            itemData = mime.data('application/x-groupLabel')
            dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.ReadOnly)
            text = QtCore.QByteArray()
            offset = QtCore.QPoint()
            dataStream >> text
            try:
                # Python v3.
                text = str(text, encoding='latin1')
            except TypeError:
                # Python v2.
                text = str(text)
                
            # reorder the groups
            from_index = eval(text)
            to_index = self.group_index
            guts.moveInPlace(self.parent.run.getGroups(),from_index,to_index)
            # you also have to change the adjacency matrix
            guts.moveInPlace(self.parent.run.getMatrix(),from_index,to_index)
            for row in self.parent.run.getMatrix():
                guts.moveInPlace(row,from_index,to_index)
                
            self.parent.setCurrentGroup(to_index)
            self.parent.syncToRun()
            
            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.ignore()

    dragMoveEvent = dragEnterEvent


class CustomComponentGroupCell(CustomGroupTextCell):
    def __init__(self,parent,text,group_index,incl):
        super(CustomComponentGroupCell, self).__init__(parent,text,group_index,incl)

    def paintBackground(self,sel):
        if sel:
            self.setStyleSheet("background-color: rgb(152,245,255)")
        else:
            self.setStyleSheet("background-color: rgb(150,150,150)")

    def mousePressEvent(self,event):
        self.parent.toggleGroup(self.group_index)

    def dragEnterEvent(self,event):
        pass

    def dropEvent(self,event):
        pass
        

class CustomFixedTextCell(QtGui.QLabel):
    def __init__(self,parent,text,array,index,sel):
        super(CustomFixedTextCell, self).__init__(parent)
        self.parent = parent
        self.index = index
        self.array_to_sort = array
        
        self.setText(text)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        if sel:
            self.setStyleSheet("background-color: rgb(152,245,255)")
        else:
            self.setStyleSheet("background-color: white")

    def mousePressEvent(self,event):
        # tell the parent widget that this is current so it can be highlighted
        self.parent.setCurrentIndex(self.index)
        # mouse dragging stuff    
        itemData = QtCore.QByteArray()
        dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.WriteOnly)
        dataStream << QtCore.QByteArray(str(self.index))
        mimeData = QtCore.QMimeData()
        mimeData.setData('application/x-rowNumber', itemData)
        self.drag = QtGui.QDrag(self.parent)
        self.drag.setMimeData(mimeData)
        self.drag.exec_()

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat('application/x-rowNumber'):
            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.ignore()

    def dropEvent(self, event):       
        if event.mimeData().hasFormat('application/x-rowNumber'):
            # unpack drag data
            mime = event.mimeData()
            itemData = mime.data('application/x-rowNumber')
            dataStream = QtCore.QDataStream(itemData, QtCore.QIODevice.ReadOnly)
            text = QtCore.QByteArray()
            offset = QtCore.QPoint()
            dataStream >> text
            try:
                # Python v3.
                text = str(text, encoding='latin1')
            except TypeError:
                # Python v2.
                text = str(text)
                
            # reorder the groups
            from_index = eval(text)
            to_index = self.index
            guts.moveInPlace(self.array_to_sort,from_index,to_index)                
            self.parent.setCurrentIndex(to_index)
            
            if self.parent.__class__.__name__ == 'CustomPhaseWidget':
                self.parent.syncToRun()
            elif self.parent.__class__.__name__ == 'CustomPhaseItemWidget':
                self.parent.syncToPhase()
            elif self.parent.__class__.__name__ == 'CustomTestSetSelectionWidget':
                self.parent.updateFrozenWidgets()

            if event.source():
                event.setDropAction(QtCore.Qt.MoveAction)
                event.accept()
            else:
                event.ignore()

    dragMoveEvent = dragEnterEvent

    def mouseDoubleClickEvent(self,event):
        if self.parent.__class__.__name__ == 'CustomPhaseWidget':
            self.parent.nameEditMode(self.index)
        elif self.parent.__class__.__name__ == 'CustomPhaseItemWidget':
            self.parent.phase.getGUI().getMainTabs().requestTab(self.array_to_sort[self.index])
            self.parent.phase.getGUI().getMainTabs().switchCurrentTab(self.array_to_sort[self.index])
        elif self.parent.__class__.__name__ == 'CustomTestSetSelectionWidget':
            self.parent.selectionBoxMode(self.index)
        

class CustomConnectionCell(QtGui.QFrame):
    def __init__(self,parent,state,group_from,group_to):
        super(CustomConnectionCell, self).__init__(parent)
        self.parent = parent
        self.groups = (group_from,group_to)
        self.setStyleSheet("QWidget { background-color: rgb(139,131,134) }")
        self.setFrameShape(QtGui.QFrame.StyledPanel)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setMouseTracking(True)

        # map states to colors
        self.color_map = {'off': QtGui.QColor(150,150,150),
                          'on': QtGui.QColor(0,255,0),
                          'bias_off': QtGui.QColor(150,150,150),
                          'bias_on': QtGui.QColor(255,185,15),
                          #'included': QtGui.QColor(255,110,180), #pink
                          'included': QtGui.QColor(152,245,255), #blue
                          'excluded': QtGui.QColor(150,150,150),
                          'dead': QtGui.QColor(0,0,0)
                          }
        self.updateState(state)
        self.show()

    def mouseMoveEvent(self,event):
        if self.groups[0] and self.groups[1]:
            self.parent.parent.setHelperText(str('Connection: '+
                                                 self.groups[0] +
                                                 ' to ' +
                                                 self.groups[1]))
        else:
            self.parent.parent.setHelperText('...')

    def getState(self):
        return self.state
        
    def updateState(self,x):
        self.state = x
        self.update()

    def paintEvent(self,event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawColorRect(qp)
        qp.end()

    def drawColorRect(self,qp):
        color = self.color_map[self.state]
        brush = QtGui.QBrush(color)
        qp.setBrush(brush)
        qp.drawRect(self.frameRect())
        
class CustomOverrideValue(QtGui.QTableWidgetItem):
    def __init__(self,index,original_param,override_param):
        super(CustomOverrideValue, self).__init__()
        self.setFlags(QtCore.Qt.ItemIsSelectable)
        self.original = original_param
        self.override = override_param
        self.oFlag = False
        self.index = index
        
        if self.override:
            self.setBackground(QtGui.QColor(255,255,0))
            # get appropriate text representation of value
            val = None
            if self.override.widget_type == 'checkbox':
                if self.override.value == 0:
                    val = 'Off'
                else:
                    val = 'On'
            elif self.override.widget_type == 'dropdown':
                val = self.override.dropdown_options[self.override.value]
            else:
                val = self.override.value
            self.setText(str(val))
            self.oFlag = True
        else:
            self.setBackground(QtGui.QColor(255,255,255))
            # get appropriate text representation of value
            val = None
            if self.original.widget_type == 'checkbox':
                if self.original.value == 0:
                    val = 'Off'
                else:
                    val = 'On'
            elif self.original.widget_type == 'dropdown':
                val = self.original.dropdown_options[self.original.value]
            else:
                val = self.original.value
            self.setText(str(val))

    def setOverride(self,override_param):
        self.override = override_param
        self.setBackground(QtGui.QColor(255,255,0))
        # get appropriate text representation of value
        val = None
        if self.override.widget_type == 'checkbox':
            if self.override.value == 0:
                val = 'Off'
            else:
                val = 'On'
        elif self.override.widget_type == 'dropdown':
            val = self.override.dropdown_options[self.override.value]
        else:
            val = self.override.value
        self.setText(str(val))
        self.oFlag = True

    def killOverride(self):
        self.setBackground(QtGui.QColor(255,255,255))
        # get appropriate text representation of value
        val = None
        if self.original.widget_type == 'checkbox':
            if self.original.value == 0:
                val = 'Off'
            else:
                val = 'On'
        elif self.original.widget_type == 'dropdown':
            val = self.original.dropdown_options[self.original.value]
        else:
            val = self.original.value
        self.setText(str(val))
        self.override = None
        self.oFlag = False

    def isOverriden(self):
        return self.oFlag

    def getIndex(self):
        return self.index


class CustomInteractiveParamWidget(QtGui.QTableWidget):
    def __init__(self,param_list,phase_item):
        super(CustomInteractiveParamWidget, self).__init__()
        self.param_list = param_list
        self.phase_item = phase_item

        self.itemClicked.connect(self.clickHandler)
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(False)
        self.setRowCount(len(self.param_list))
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Parameter','Value'])
        self.setFixedSize(self.width(),self.verticalHeader().length() + 25)
        # trim param list so you only see overridable params
        self.param_list = [x for x in self.param_list if
                           x.override_flag == 1]
        # what is the longest parameter name? make the first col fit it
        plengths = [len(x.form_name) for x in self.param_list]
        max_length = max(plengths)
        self.setColumnWidth(0,self.fontMetrics().width('x'*max_length))
        

        for i,param in enumerate(self.param_list):
            self.setCellWidget(i,0,QtGui.QLabel(param.form_name))
            # is this param in our overrides list?
            o = [x for x in self.phase_item.getOverrides()
                 if param.variable_name == x.variable_name]
            if o:
                self.setItem(i,1,CustomOverrideValue(i,param,o[0]))
            else:
                self.setItem(i,1,CustomOverrideValue(i,param,None))

    def clickHandler(self,item):
        if not item.isOverriden():
            self.overrideRequested(item.getIndex())
        else:
            item.killOverride()
            # remove from phase_item overrides list
            selected = [x for x in self.phase_item.getOverrides()
                        if self.param_list[item.getIndex()].variable_name == x.variable_name]
            self.phase_item.getOverrides().remove(selected[0])
            

    def overrideRequested(self,i):
        oe = OverrideEditor(self.phase_item.getGUI(),
                            self.param_list[i],
                            self.phase_item)
        ret =  oe.exec_()
        if ret == 1:
            selected = [x for x in self.phase_item.getOverrides()
                        if self.param_list[i].variable_name == x.variable_name]
            self.item(i,1).setOverride(selected[0])
        else:
            pass

class CustomRecordingWidget(QtGui.QTableWidget):
    '''Doc here
    '''
    def __init__(self,parent,phase_item):
        super(CustomRecordingWidget, self).__init__(parent)
        self.parent = parent
        self.phase_item = phase_item
        self.run = phase_item.parent.parent
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.setShowGrid(False)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(True)
        self.cellClicked.connect(self.clickHandler)
        img = QtGui.QPixmap(os.path.join(os.getcwd(),
                                         'resources','images',
                                         'on_rocker.png'))
        self.cell_width = img.width()
        self.cell_height = img.height()
        # size
        
        # initialize
        self.syncToRun()

    def getOn(self):
        pic = QtGui.QPixmap(os.path.join(os.getcwd(),
                                         'resources','images',
                                         'on_rocker.png'))
        widget = QtGui.QLabel()
        widget.setPixmap(pic)
        return widget

    def getOff(self):
        pic = QtGui.QPixmap(os.path.join(os.getcwd(),
                                         'resources','images',
                                         'off_rocker.png'))
        widget = QtGui.QLabel()
        widget.setPixmap(pic)
        return widget
        
    def syncToRun(self):
    	# first make sure recording data in the data structure is up to date
    	group_names = [x['name'] for x in self.run.getGroups()]
        for group in self.phase_item.recording_data:
            if group not in group_names:
                self.phase_item.removeRecordingEntry(group)
                
        self.clear()
        self.setRowCount(len(self.phase_item.getComponentGroups()))
        self.setColumnCount(self.run.getValueOf('ticks'))
        group_labels = sorted(self.phase_item.getComponentGroups())
        time_labels = range(1,self.run.getValueOf('ticks')+1)
        time_labels = [str('t'+str(x)) for x in time_labels]
        self.setHorizontalHeaderLabels(time_labels)
        self.setVerticalHeaderLabels(group_labels)

        self.updateRecordingMatrix()

    def updateRecordingMatrix(self):
        matrix = self.phase_item.getRecordingMatrix()
        if not matrix:
        	return
        for c in range(len(matrix[0])):
            self.setColumnWidth(c,self.cell_width)
        for r in range(len(matrix)):
            self.setRowHeight(r,self.cell_height)
            for c in range(len(matrix[0])):
                switch_widget = None
                if matrix[r][c] == 1:
                    switch_widget = self.getOn()
                else:
                    switch_widget = self.getOff()

                self.setCellWidget(r,c,switch_widget)

    def clickHandler(self,i,j):
        self.toggleState(i,j)
        
    def toggleState(self,i,j):
        self.phase_item.toggleRecord(i,j)
        self.updateRecordingMatrix()
        

class CustomDeleteTestLinkLabel(QtGui.QTableWidgetItem):
    def __init__(self,index):
        super(CustomDeleteTestLinkLabel, self).__init__()
        self.setFlags(QtCore.Qt.ItemIsSelectable)
        self.index = index
        self.setText('Unlink')

    def getIndex(self):
        return self.index


class CustomTestSetSelectionWidget(QtGui.QTableWidget):
    def __init__(self,phase_item):
        super(CustomTestSetSelectionWidget, self).__init__()
        self.phase_item = phase_item
      
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.itemClicked.connect(self.clickHandler)
        self.horizontalHeader().setVisible(False)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setRowCount(1 + len(self.phase_item.getTestProfiles()))
        self.setColumnCount(2)
        self.horizontalHeader().setStretchLastSection(True)
        
        # sync
        self.syncToPhaseItem()

    def linkToTestSet(self):
        if len(self.phase_item.getGUI().getScript().getTestProfiles().getChildren()) == 0:
            dialogs.showWarning(self,'No test sets are defined.')
            return
        d = LinkToTestEditor(self.phase_item.getGUI(),self.phase_item)
        ret = d.exec_()
        if ret == 1:
            self.syncToPhaseItem()

    def clickHandler(self,item):
        i = item.getIndex()
        self.phase_item.clearTestProfile(i)
        # update
        self.syncToPhaseItem()
        
    def syncToPhaseItem(self):
        self.clear()
        self.setRowCount(1 + len(self.phase_item.getTestProfiles()))
        # add test set button goes in first row
        link_btn = QtGui.QPushButton('Add Link')
        link_btn.clicked.connect(self.linkToTestSet)
        self.setCellWidget(0,0,link_btn)
        self.setCellWidget(0,1,QtGui.QLabel('')) # dummy label
        # now make rows for test sets that have already been added
        for i in range(1,len(self.phase_item.getTestProfiles())+1):
            self.setCellWidget(i,0,QtGui.QLabel(self.phase_item.getTestProfiles()[i-1]))
            self.setItem(i,1,CustomDeleteTestLinkLabel(i-1))
        self.resizeColumnsToContents()
        
class CustomWeightTypeBox(QtGui.QComboBox):
    def __init__(self,parent,conn_string):
        super(CustomWeightTypeBox, self).__init__(parent)
        self.parent = parent
        self.conn_string = conn_string
        
        self.addItem('NO_NOISE')
        self.addItem('ADDITIVE_NOISE')
        self.addItem('MULTIPLICATIVE_NOISE')
        
    def wireSignal(self):
        self.currentIndexChanged.connect(lambda i: 
                       self.parent.updateWeightType(self.conn_string,i))
                       
        
class CustomNoiseValueBox(QtGui.QDoubleSpinBox):
    def __init__(self,parent,name_string):
        super(CustomNoiseValueBox, self).__init__(parent)
        self.parent = parent
        self.name_string = name_string # could be a connection or a group name
        
        self.setMinimum(0)
        self.setMaximum(10)
        self.setDecimals(3)
        self.setSingleStep(.001)
        
    def wireSignal(self):
        self.valueChanged.connect(lambda v: 
                        self.parent.updateNoiseValue(self.name_string,v))
        
        
class CustomWeightNoiseWidget(QtGui.QTableWidget):
    def __init__(self,phase_item):
        super(CustomWeightNoiseWidget, self).__init__()
        self.phase_item = phase_item
      
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setRowCount(1) # will change dynamically
        self.setColumnCount(3)
        self.setHorizontalHeaderLabels(['Connection','Noise type','Noise value'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0,self.fontMetrics().width('x'*28))
        
        # update
        self.syncToPhaseItem()
        
        
    def syncToPhaseItem(self):
        self.setRowCount(len(self.phase_item.getComponentConnections()))
        weight_data = self.phase_item.getWeightNoiseData()
        run = self.phase_item.parent.parent
        # need to iterate over all available connections. these are found in the 
        # 'connections' entry of net_components
        for i,conn in enumerate(self.phase_item.getComponentConnections()):
            self.setCellWidget(i,0,QtGui.QLabel(conn.replace('%','->')))
            type_box = CustomWeightTypeBox(self,conn)
            self.setCellWidget(i,1,type_box)
            value_box = CustomNoiseValueBox(self,conn)
            self.setCellWidget(i,2,value_box)
            # default (when no entry exists) is NO weight noise and value of 0
            # first find out if this group has a value in noise_data
            if conn in weight_data:
                # there is a value associated with this. 
                type_box.setCurrentIndex(weight_data[conn][0])
                value_box.setValue(weight_data[conn][1])
            else:
                # no value, use default settings
                pass
            type_box.wireSignal()
            value_box.wireSignal()
                
    def updateWeightType(self,conn,i):
        if i == 0:
            # remove the connection's noise data
            self.phase_item.removeNoiseRecord('weight_noise',conn)
            self.syncToPhaseItem()
        else:
            self.phase_item.setWeightNoiseType(conn,i)
            
    def updateNoiseValue(self,conn,val):
        if val == 0.0:
            # remove the connection's noise data
            self.phase_item.removeNoiseRecord('weight_noise',conn)
            self.syncToPhaseItem()
        else:
            self.phase_item.setWeightNoiseValue(conn,val)
   
            
class CustomActivationNoiseWidget(QtGui.QTableWidget):
    def __init__(self,phase_item):
        super(CustomActivationNoiseWidget, self).__init__()
        self.phase_item = phase_item
      
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setRowCount(1) # will change dynamically
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Group','Noise value'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0,self.fontMetrics().width('x'*28))
        
        # update
        self.syncToPhaseItem()
        
        
    def syncToPhaseItem(self):
        self.setRowCount(len(self.phase_item.getComponentGroups()))
        activation_data = self.phase_item.getActivationNoiseData()
        run = self.phase_item.parent.parent
        # need to iterate over all available groups. these are found in the 
        # 'groups' entry of net_components
        for i,g in enumerate(self.phase_item.getComponentGroups()):
            self.setCellWidget(i,0,QtGui.QLabel(g))
            value_box = CustomNoiseValueBox(self,g)
            self.setCellWidget(i,1,value_box)
            # default (when no entry exists) is NO weight noise and value of 0
            # first find out if this group has a value in noise_data
            if g in activation_data:
                # there is a value associated with this. 
                value_box.setValue(activation_data[g])
            else:
                # no value, use default settings
                pass
            value_box.wireSignal()
            
    def updateNoiseValue(self,g,val):
        if val == 0.0:
            # remove the group's noise data
            self.phase_item.removeNoiseRecord('activation_noise',g)
            self.syncToPhaseItem()
        else:
            self.phase_item.setActivationNoiseValue(g,val)


class CustomInputNoiseWidget(QtGui.QTableWidget):
    def __init__(self,phase_item):
        super(CustomInputNoiseWidget, self).__init__()
        self.phase_item = phase_item
      
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        self.horizontalHeader().setVisible(True)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setRowCount(1) # will change dynamically
        self.setColumnCount(2)
        self.setHorizontalHeaderLabels(['Group','Noise value'])
        self.horizontalHeader().setStretchLastSection(True)
        self.setColumnWidth(0,self.fontMetrics().width('x'*28))
        
        # update
        self.syncToPhaseItem()
        
        
    def syncToPhaseItem(self):
        self.setRowCount(len(self.phase_item.getComponentGroups()))
        input_data = self.phase_item.getInputNoiseData()
        run = self.phase_item.parent.parent
        # need to iterate over all available groups. these are found in the 
        # 'groups' entry of net_components
        for i,g in enumerate(self.phase_item.getComponentGroups()):
            self.setCellWidget(i,0,QtGui.QLabel(g))
            value_box = CustomNoiseValueBox(self,g)
            self.setCellWidget(i,1,value_box)
            # default (when no entry exists) is NO weight noise and value of 0
            # first find out if this group has a value in noise_data
            if g in input_data:
                # there is a value associated with this. 
                value_box.setValue(input_data[g])
            else:
                # no value, use default settings
                pass
            value_box.wireSignal()
            
    def updateNoiseValue(self,g,val):
        if val == 0.0:
            # remove the group's noise data
            self.phase_item.removeNoiseRecord('input_noise',g)
            self.syncToPhaseItem()
        else:
            self.phase_item.setInputNoiseValue(g,val)
            
            
class CustomApplyIterationWidget(QtGui.QListWidget):
    def __init__(self,iterator):
        super(CustomApplyIterationWidget, self).__init__()
        self.iterator = iterator
      
        self.setSizePolicy(QtGui.QSizePolicy.Expanding,
                           QtGui.QSizePolicy.Expanding)
        # no signal for catching changes to listwidgetitem states
        # so do it with this method
        self.itemChanged.connect(self.toggleCheck)
        
        self.updateLines()
                    
    def updateLines(self):
        self.clear()
        # fill out the list
        for path in self.iterator.getPotentialPaths():
            # is path already included?
            if (self.iterator.getAppliedPaths() != 'ALL') \
                and (path in self.iterator.getAppliedPaths()):
                state = QtCore.Qt.Checked
            else:
                state = QtCore.Qt.Unchecked
            self.addItem(CustomApplyLine(path,state))
            
    def toggleCheck(self,item):
        if item.checkState() == QtCore.Qt.Checked:
            # only update iterator paths if this isn't already there
            if item.text() not in self.iterator.getAppliedPaths():
                self.iterator.addAppliedPath(item.text())
        else:
            self.iterator.removeAppliedPath(item.text())
            

class CustomApplyLine(QtGui.QListWidgetItem):
    def __init__(self,text,state):
        super(CustomApplyLine,self).__init__()
        self.setText(text)
        self.setCheckState(state)
        