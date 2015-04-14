from PySide import QtGui,QtCore,QtSql
import argparse
import numpy as np
import matplotlib.pyplot as plt
import getpass
import sys
import os

def queryVariables():
    while True:
        sys.stdout.write('Type variable names to extract, separated by commas.\n')
        sys.stdout.write('Spaces will be ignored.\n')
        sys.stdout.write('--> ')
        resp = raw_input().lower()
        return resp

def querySaveOrPlot():
    while True:
        sys.stdout.write('What are we going to do with the data?\n')
        sys.stdout.write('Select option: 0 = save, 1 = plot, 2 = both\n')
        sys.stdout.write('--> ')
        resp = raw_input().lower()
        return resp

def queryPlotType():
    while True:
        sys.stdout.write('What kind of plot are we making?\n')
        sys.stdout.write('Select option: 0 = scatter, 1 = line\n')
        sys.stdout.write('--> ')
        resp = raw_input().lower()
        return resp
    
def queryOutput():
    while True:
        sys.stdout.write('For saving, type the name of the output file with desired extension.\n')
        sys.stdout.write('Output file will be tab-delimited.\n')
        sys.stdout.write('--> ')
        resp = raw_input().lower()
        return resp

def queryConstraints():
    while True:
        sys.stdout.write('Enter constraints on values (if any).\n')
        sys.stdout.write('Use of logical operators "AND" and "OR", and parentheses are supported.\n')
        sys.stdout.write('e.g. epsilon <= 0.5 AND (run_name = "xor" OR run_name = "xor2")\n')
        sys.stdout.write('--> ')
        resp = raw_input().lower()
        return resp

def getFields(db,table):
    fieldList = []
    q = QtSql.QSqlQuery(db)
    q.exec_('select * from '+table+' LIMIT 0,0')
    rec = q.record()
    for i in range(rec.count()):
        fieldList.append((rec.fieldName(i),
                          str(rec.field(i).type())))
    return fieldList

def getRecordCount(db,table):
    q = QtSql.QSqlQuery(db)
    q.exec_(str('select COUNT(*) from '+table))
    if q.next():
        return str(q.value(0))
    else:
        return '0'

def buildQueryString(varDict,usrVars,usrConst,lhs,rhs):
    # find all the tables that will need to be joined
    tables = []
    for x in usrVars:
        tnames = varDict[x][1]
        for t in tnames:
            tables.append(t)
    for x in lhs:
        tnames = varDict[x][1]
        for t in tnames:
            tables.append(t)
    for x in rhs:
        if x in varDict:
            tnames = varDict[x][1]
            for t in tnames:
                tables.append(t)
                
    tables = list(set(tables))
    queryString = 'select ' +\
                  ','.join(usrVars) +\
                  ' from ' +\
                  ' natural join '.join(tables)
    
    if usrConst:
        queryString += ' where '
        queryString += usrConst
        
    queryString += ' order by '
    queryString += usrVars[0]
        
    queryString += ';'
    
    return queryString
                  

def getColumns(db,varDict,usrVars,queryString):
    columns = []
    for v in usrVars:
        # make an empty list in 'columns' that will become this variable's numpy array
        columns.append([])

    q = QtSql.QSqlQuery(db)
    q.setForwardOnly(True)
    q.exec_(queryString)
    while q.next():
        for i,v in enumerate(usrVars):
            if varDict[v][0] == "<type 'int'>":
                columns[i].append(int(q.value(i)))
            elif varDict[v][0] == "<type 'float'>":
                columns[i].append(float(q.value(i)))
            elif varDict[v][0] == "<type 'unicode'>":
                columns[i].append(str(q.value(i)))
                
    # convert columns to numpy arrays, paying attention to type
    for i,v in enumerate(usrVars):
        if varDict[v][0] == "<type 'int'>":
            columns[i] = np.array(columns[i],dtype=np.int32)
        elif varDict[v][0] == "<type 'float'>":
            columns[i] = np.array(columns[i],dtype=np.float64)
        elif varDict[v][0] == "<type 'unicode'>":
            columns[i] = np.array(columns[i],dtype=np.object)
        
    return columns

def writeOutput(cols,outfile):
    with open(outfile,'w') as f:
        # rows
        for i in range(len(cols[0])):
            # cols
            for j in range(len(cols)):
                f.write(str(cols[j][i]))
                if j < len(cols)-1:
                    f.write('\t')
            f.write('\n')
            
def plotOutput(mode,cols,headers):
    if mode == 0:
        if len(cols) != 2:
            print 'Plot error: expected 2 columns, but got',len(cols)
            sys.exit(0)
        for c in cols:
            if c.dtype not in [np.float64,np.int32]:
                print 'Plot error: can only plot numeric data'
                sys.exit(0)
        # scatter
        plt.scatter(cols[0],cols[1])
        plt.xlabel(headers[0])
        plt.ylabel(headers[1])
    elif mode == 1:
        # line. two cases: single line or series
        if len(headers) == 2:
            # single case
            for c in cols:
                if c.dtype not in [np.float64,np.int32]:
                    print 'Plot error: can only plot numeric data'
                    sys.exit(0)
                
            plt.plot(cols[0],cols[1])
            plt.xlabel(headers[0])
            plt.ylabel(headers[1])
        elif len(headers) == 3:
            # multi-line series
            if cols[1].dtype not in [np.float64,np.int32] or\
                cols[2].dtype not in [np.float64,np.int32]:
                print 'Plot error: can only plot numeric data for cols 2 and 3.'
                sys.exit(0)
            series_id = None
            x = []
            y = []
            legend = []
            for i in range(np.size(cols[0])):
                # iterate over rows
                # cols[0] holds the series identifier
                if cols[0][i] != series_id:
                    if series_id:
                        # add old series to the plot
                        plt.plot(np.array(x,dtype=cols[1].dtype),
                                np.array(y,dtype=cols[2].dtype))
                    # new series
                    x = []
                    y = []
                    series_id = cols[0][i]
                    legend.append(series_id)
                x.append(cols[1][i])
                y.append(cols[2][i])
            # don't show legend if there are too many entries
            if len(legend) < 11:
                plt.legend(legend, loc='upper left', title=headers[0])
            plt.xlabel(headers[1])
            plt.ylabel(headers[2])
        else:
            print 'Plot error: expected 2 or 3 columns, but got',len(headers)
            sys.exit(0)
    plt.show()

def connectToDB(driver,host,name,user,pw):
    db = QtSql.QSqlDatabase.addDatabase(driver)
    db.setHostName(host)
    db.setDatabaseName(name)
    db.setUserName(user)
    db.setPassword(pw)
    ok = db.open()
    if not ok:
        return None
    else:
        return db
        
def run(args):
    # do we need to ask for password?
    if args.user != '':
        pw = getpass.getpass('Please enter '+str(args.user)+"'s password: ")
    else:
        pw = ''
        
    # establish connection to database and print name
    db = connectToDB(args.driver,args.host,args.database,args.user,pw)
    if not db:
        print 'Error, could not connect to database.'
        sys.exit(0)
    print '''
---------------------------------------------------------------------------
                                                     
MikeNetGUI Copyright (C) 2013-2014 Robert Powers

Developed at Haskins Laboratories, New Haven, CT.
(http://www.haskins.yale.edu/)

This program comes with ABSOLUTELY NO WARRANTY; for details see README file.
This is free software, and you are welcome to redistribute it
under certain conditions; see README file or click Help->About for details.

---------------------------------------------------------------------------

Press Ctrl+C to exit at any time.
'''
    print ''
    print 'DATABASE NAME:',os.path.split(args.database)[1]
    print ''
        
    # print table and variable names, and create a dictionary mapping
    # variables (values) to their respective tables (keys)
    print 'TABLES:'
    print ''
    gap = ' '*4
    tables = [str(x) for x in db.tables()]
    varDict = {}
    for table in tables:
        print gap,'Name:',table
        print gap,'Records:',getRecordCount(db,table)
        print gap,'Variables:'
        fields = getFields(db,table)
        for fname,ftype in fields:
            print 2*gap + fname + gap + ftype
            if fname not in varDict:
                varDict[fname] = ['',[]]
            varDict[fname][0] = ftype
            varDict[fname][1].append(table)

        print ''
    # manually override tables for id and run_id to just metadata
    varDict['id'] = [varDict['id'][0],['metadata']]
    varDict['run_id'] = [varDict['run_id'][0],['metadata']]
    
    # query variables
    while True:
        usrVars = queryVariables().split(',')
        usrVars = [x.replace(' ','') for x in usrVars]
        mistypes = [x for x in usrVars if x not in varDict]
        if not mistypes:
            print ''
            break
        else:
            print ''
            print ','.join(mistypes) + ' not found in database. Try again.'
            print ''

    # query constraints
    lhs = []
    rhs = []
    while True:
        lhs = []
        rhs = []
        usrConst = queryConstraints()
        if usrConst == '':
            usrConst = None
            print ''
            break

        ops = ['<>','!=','>=','<=','=','>','<','between','like','in']
        # remove logicals and parens
        const = usrConst
        const = const.replace(' and ','@')
        const = const.replace(' or ','@')
        const = const.replace('(','@')
        const = const.replace(')','@')
        const = const.split('@')
        const = [x.replace(' ','') for x in const if len(x)>0 and x != ' ']
        # find references to variables and check that they exist
        for x in const:
            for op in ops:
                if op in x:
                    l,r = x.split(op)
                    lhs.append(l)
                    rhs.append(r)
                    break
                      
        mistypes = [x for x in lhs if x not in varDict]
        if not mistypes:
            print ''
            break
        else:
            print ''
            print ','.join(mistypes) + ' not found in database. Try again.'
            print ''

    # how is the data being handled?
    mode = 0
    outfile = None
    plotting = False
    while True:
        mode = querySaveOrPlot()
        try:
            mode = int(mode)
            if mode in range(3):
                print ''
                break
            else:
                print ''
                print 'Unrecognized option.'
                print ''
        except:
            print ''
            print 'Unrecognized option.'
            print ''
            
    if mode in [0,2]:
        # saving
        outfile = queryOutput()
        print ''
    if mode in [1,2]:
        while True:
            plotting = queryPlotType()
            try:
                plotting = int(plotting)
                if plotting in range(2):
                    print ''
                    break
                else:
                    print ''
                    print 'Unrecognized option.'
                    print ''
            except:
                print ''
                print 'Unrecognized option.'
                print ''
            
    # finally, build/execute query
    print 'fetching data...'
    queryString = buildQueryString(varDict,usrVars,usrConst,lhs,rhs)
    cols = getColumns(db,varDict,usrVars,queryString)
    if mode in [0,2]:
        print 'writing output...'
        writeOutput(cols,outfile)
    if mode in [1,2]:
        print 'preparing plot...'
        plotOutput(plotting,cols,usrVars)
    print 'done'

def main():
    try: 
        app = QtGui.QApplication([])
            
    except RuntimeError:
        app = QtCore.QCoreApplication.instance()
        
    parser = argparse.ArgumentParser(description='Extract columns of data from a database.')
    parser.add_argument('database',help='database name plus extension. e.g. mydata.db')
    parser.add_argument('-driver',help='database driver',choices=['QSQLITE','QMYSQL','QPSQL'],
                        default='QSQLITE')
    parser.add_argument('-host',help='database host',default='localhost')
    parser.add_argument('-user',help='database username',default='')
    args = parser.parse_args()
    run(args)

        
if __name__ == '__main__':
    main()
