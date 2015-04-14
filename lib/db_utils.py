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
from PySide import QtSql
import glob
import os
import gen_utils as guts

def decodeDriver(gui):
    driver_string = 'QSQLITE'
    if not gui:
        return driver_string
    param = gui.parameters['database_driver']
    option = param.dropdown_options[param.value]
    if option == 'IBM DB2':
        driver_string = 'QDB2'
    elif option == 'Borland InterBase Driver':
        driver_string = 'QIBASE'
    elif option == 'MySQL Driver':
        driver_string = 'QMYSQL'
    elif option == 'Oracle Call Interface Driver':
        driver_string = 'QOCI'
    elif option == 'ODBC Driver (includes Microsoft SQL Server)':
        driver_string = 'QODBC'
    elif option == 'PostgreSQL Driver':
        driver_string = 'QPSQL'
    elif option == 'SQLite version 3 or above':
        driver_string = 'QSQLITE'
    elif option == 'SQLite version 2':
        driver_string = 'QSQLITE2'
    elif option == 'Sybase Adaptive Server':
        driver_string = 'QTDS'

    return driver_string

def connectToDB(gui,driver,cname):
    db = QtSql.QSqlDatabase.addDatabase(driver,cname)
    db.setHostName(gui.parameters['database_host_name'].value)
    db.setDatabaseName(gui.parameters['database_path'].value)
    db.setUserName(gui.parameters['database_user_name'].value)
    db.setPassword(gui.parameters['database_password'].value)
    ok = db.open()
    if not ok:
        return None
    else:
        return db

def testDB(driver):
    db = QtSql.QSqlDatabase.addDatabase(driver)
    db.setDatabaseName('testdb.db')
    ok = db.open()
    if not ok:
        return None
    else:
        return db

def pushRunData(path,gui):
    driver = decodeDriver(gui)    
    # connect to database
    # to run as a standalone test, call with gui == None
    if not gui:
        db = testDB(driver)
    else:
        # need unique connection name. use name of folder, which is the run name
        garbage,run_name = os.path.split(path)
        db = connectToDB(gui,driver,run_name) # for real life
    
    if not db:
        # return path if there was a problem so it can be reported
        return path
    
    ###############################################################
    # create tables (if a new database)
    initializeTables(path,db,driver)
    test_fields = initializeTestTables(path,db,driver)

    # get a unique index for this whole run
    run_index = getRunIndex(db)
    
    # create a dict to map phase item names to unique indices
    phase_item_map = {}
    
    # push metadata AND group data if metadata file exists
    f_list = glob.glob(os.path.join(path,'*.metadata'))
    for f in f_list:
        # open the metadata file
        with open(f,'rU') as src:
            for line in src:
                # skip empty lines
                if line == '\n':
                    pass
                elif 'GROUP\t' in line:
                    # pushing group record
                    data = line.split('\t')
                    data = [x for x in data if len(x) > 1]
                    # get rid of 'GROUP' tag
                    data = data[1:]
                    column_names = []
                    values = []
                    for d in data:
                        l,r = guts.evaluateEq(d)
                        r = guts.smartEval(r)
                        if str(l) == 'phase_item':
                            if str(r) not in phase_item_map:
                                assignUnusedIndex(db,str(r),phase_item_map)
                            column_names.insert(0,'run_id')
                            values.insert(0,run_index)
                            column_names.insert(0,'id')
                            values.insert(0,phase_item_map[str(r)])
                            # don't actually write the phase item name.
                            # it's only needed to obtain the unique id
                        else:
                            # not phase item name, so write this entry
                            column_names.append(str(l))
                            values.append(str(r))
                            
                    pushRecord(db,'groupdata',column_names,values)
                    
                else:
                    # pushing metadata record
                    # push each column individually to be robust against
                    # changes in column order
                    data = line.split('\t')
                    data = [x for x in data if len(x) > 1]
                    column_names = []
                    values = []
                    for d in data:
                        l,r = guts.evaluateEq(d)
                        column_names.append(str(l))
                        values.append(str(r))
                        if str(l) == 'phase_item':
                            # in metadata, each row needs to be unique
                            # and needs to include phase item and run names
                            assignUnusedIndex(db,str(r),phase_item_map)
                            column_names.insert(0,'run_id')
                            values.insert(0,run_index)
                            column_names.insert(0,'id')
                            values.insert(0,phase_item_map[str(r)])
                            
                    pushRecord(db,'metadata',column_names,values)


    # same for error and noise (both are taken from the log file)
    f_list = glob.glob(os.path.join(path,'*.log'))
    for f in f_list:
        with open(f,'rU') as src:
            srclines = src.readlines()
            srclines = [x.replace('\n','') for x in srclines]
            # error first
            lines = [x for x in srclines if 'avgError:' in x]
            for l in lines:
                lsplit = l.split('\t')
                # make sure the id is unique, get a new one if necessary
                if lsplit[1] not in phase_item_map:
                    assignUnusedIndex(db,str(lsplit[1]),phase_item_map)
                lsplit[0] = phase_item_map[str(lsplit[1])]
                lsplit.insert(0,run_index)
                # don't need phase item name in the actual record
                lsplit.pop(2)
                pushRecord(db,'errordata',
                           ['run_id','id','run_trial','trial','error'],
                           lsplit)
            # then noise
            lines = [x for x in srclines if 'noiseData:' in x]
            for l in lines:
                lsplit = l.split('\t')
                # make sure the id is unique, get a new one if necessary
                if lsplit[1] not in phase_item_map:
                    assignUnusedIndex(db,str(lsplit[1]),phase_item_map)
                lsplit[0] = phase_item_map[str(lsplit[1])]
                lsplit.insert(0,run_index)
                # don't need phase item name in the actual record
                lsplit.pop(2)
                pushRecord(db,'noisedata',
                           ['run_id','id','noise_type','noise_object','noise_amount'],
                           lsplit)

    # same for activations
    

    # same for test output
    f_list = glob.glob(os.path.join(path,'*.test'))
    for f in f_list:
        trash,name_plus = os.path.split(f)
        f_split = name_plus.split('_')
        test_name = str(f_split[0])
        run_trial = str(f_split[1])
        with open(f,'rU') as src:
            for line in src:
                # add run_id and run_trial to the data entry
                data = line.split('\t')
                data.insert(0,str(run_trial))
                data.insert(0,str(run_index))
                if data[-1] == '\n':
                    data = data[:-1]
                pushRecord(db,test_name,test_fields[:len(data)],data)
                
            
    db.close()
    return None

def getRunIndex(db):
    q = QtSql.QSqlQuery(db)
    q.exec_('select MAX(run_id) as "my max" from metadata;')
    if q.next():
        fieldNo = q.record().indexOf("my max");
        if q.value(fieldNo):
            new_val = int(q.value(fieldNo)) + 1
        else:
            new_val = 1
    else:
        new_val = 1
    return new_val
    
def assignUnusedIndex(db,phase_item_name,phase_item_map):
    q = QtSql.QSqlQuery(db)
    q.exec_('select MAX(id) as "my max" from metadata;')
    if q.next():
        fieldNo = q.record().indexOf("my max");
        if q.value(fieldNo):
            new_val = int(q.value(fieldNo)) + 1
        else:
            new_val = 1
    else:
        new_val = 1
    phase_item_map[phase_item_name] = new_val

def initializeTables(path,db,driver):
    # map python datatypes to sql datatypes
    type_map = {}
    if driver == 'QSQLITE':
        type_map = {int: 'INTEGER',
                    float: 'REAL',
                    str: 'TEXT'}
    elif driver == 'QMYSQL':
        type_map = {int: 'INT',
                    float: 'FLOAT',
                    str: 'TEXT'}
    # metadata
    # get the field names from the metadata file in this directory
    fields = ['id '+type_map[int],'run_id '+type_map[int]]
    f_list = glob.glob(os.path.join(path,'*.metadata'))
    for f in f_list:
        # open the metadata file
        with open(f,'rU') as src:
            for line in src:
                # skip empty lines
                if line == '\n':
                    pass
                elif 'GROUP\t' not in line:
                    data = line.split('\t')
                    data = [x for x in data if len(x) > 1]
                    for d in data:
                        l,r = guts.evaluateEq(d)
                        r = guts.smartEval(r)
                        fields.append(str(str(l) + ' ' +
                                          type_map[type(r)]))
    fields = list(set(fields))
    field_str = ','.join(fields)
    q = QtSql.QSqlQuery(db)
    q.exec_(str('create table if not exists metadata(' +
                field_str + ');'))
    
    # groupdata
    # group fields and datatypes are going to be more restricted
    q = QtSql.QSqlQuery(db)
    q.exec_(str('create table if not exists groupdata(' +
                'id ' + type_map[int] +
                ',run_id ' + type_map[int] +
                ',group ' + type_map[str] +
                ',units ' + type_map[int] +
                ',activation_type ' + type_map[str] +
                ',error_computation_type ' + type_map[str] +
                ');'))

    # errordata
    q = QtSql.QSqlQuery(db)
    q.exec_(str('create table if not exists errordata(' +
                'id ' + type_map[int] +
                ',run_id ' + type_map[int] +
                ',run_trial ' + type_map[int] +
                ',trial ' + type_map[int] +
                ',error ' + type_map[float] +
                ');'))
    
    # activationdata
    
    # noisedata
    q = QtSql.QSqlQuery(db)
    q.exec_(str('create table if not exists noisedata(' +
                'id ' + type_map[int] +
                ',run_id ' + type_map[int] +
                ',noise_type ' + type_map[str] +
                ',noise_object ' + type_map[str] +
                ',noise_amount ' + type_map[float] +
                ');'))

def initializeTestTables(path,db,driver):
    # map python datatypes to sql datatypes
    type_map = {}
    if driver == 'QSQLITE':
        type_map = {int: 'INTEGER',
                    float: 'REAL',
                    str: 'TEXT'}
    elif driver == 'QMYSQL':
        type_map = {int: 'INT',
                    float: 'FLOAT',
                    str: 'TEXT'}
    # testdata
    fields = ['run_id '+type_map[int],'run_trial '+type_map[int]]
    if os.path.isfile(os.path.join(path,'test_headers')):
        with open(os.path.join(path,'test_headers'),'rU') as src:
            for line in src:
                # skip empty lines
                if line == '\n':
                    pass
                else:
                    fields.append(line)
                    
    field_str = ','.join(fields)
    # we want to build a table for each test
    unique_test_names = []
    f_list = glob.glob(os.path.join(path,'*.test'))
    for f in f_list:
        trash,f = os.path.split(f)
        f_split = f.split('_')
        test_name = f_split[0]
        if test_name not in unique_test_names:
            q = QtSql.QSqlQuery(db)
            q.exec_(str('create table if not exists ' + test_name +
                        '(' + field_str + ');'))
            unique_test_names.append(test_name)
        
    split_fields = [x.split() for x in fields]
    return [x for x,y in split_fields] # returns only field names


def pushRecord(db,table_name,column_names,values):
    q = QtSql.QSqlQuery(db)
    column_data = ','.join(column_names)
    qmarks = ['?']*len(values)
    qmarks = ','.join(qmarks)

    q.prepare(str('insert into ' + table_name + '(' +
                  column_data + ') values (' + qmarks + ');'))
    for v in values:
        q.addBindValue(v)
    q.exec_()

        
####TEST code
from PySide import QtCore,QtGui
import sys
class MainApp(QtGui.QMainWindow):
    '''Main application window is the top-level widget.'''
    def __init__(self):
        super(MainApp, self).__init__()
        pushRunData(os.getcwd(),None)
        
def main(): 
        try: 
            app = QtGui.QApplication(sys.argv)
            
        except RuntimeError:
            app = QtCore.QCoreApplication.instance()
        
        gui = MainApp()
        app.processEvents()
        app.exec_()
        


if __name__ == '__main__':
    main()

