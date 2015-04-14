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
import multiprocessing as mp
from itertools import product
from run_compiler import compileRun
import subprocess
from time import sleep
from math import ceil
import re
import os
import random
import decimal

# ugly global variables to get around various threading issues
prepared_runs = []
main_directory = os.getcwd()

def worker(args):
    global prepared_runs
    global main_directory
    run_index,queue,lock = args
    ret_code = compileRun(prepared_runs[run_index],main_directory)
    with lock:
    	queue.put(ret_code)
    return ret_code
            
            

class ScriptThread(QtCore.QThread):
    # define custom signals that will update the progress display
    # in the main thread...that's the only way to communicate
    cpus_counted = QtCore.Signal(int)
    total_progress = QtCore.Signal(int,int)
    success_ratio = QtCore.Signal(int,int)
    
    def __init__(self,script):
        super(ScriptThread,self).__init__(script.getGUI())
        global prepared_runs
        prepared_runs = []
        
        self.script = script
        
        # connect custom signals
        self.cpus_counted.connect(script.getTabWidget().updateCores)
        self.total_progress.connect(script.getTabWidget().updateTotalProgress)
        self.success_ratio.connect(script.getTabWidget().updateSuccessRatio)
        
    def run(self):
        global prepared_runs
        # go through the script and prepare runs.
        # this step involves computing values in iterated runs
        for child in self.script.getChildren():
            if child.getClassName() == 'MikenetRun':
                # flush previous overrides (if any exist)
                child.clearRunOverrides()
                # get a naked copy of the run (not the original)
                prepared_runs.append(child.getCopy())
            else:
                prepared_runs += self.getIteratedRuns(child)

        #DEBUG
        for r in prepared_runs:
            print 'run o',r.getRunOverrides()
        
        # are we doing multiprocessing or not?
        if self.script.getGUI().parameters['multiprocessing'].value == 1:
            num_cores = self.available_cpu_count()
            # are we limiting the number of cpus?
            actually_using = None
            cap = self.script.getGUI().parameters['max_cpus'].value
            if cap.strip() == '':
                actually_using = num_cores
            try:
                actually_using = min([int(cap.strip()),num_cores])
            except:
                actually_using = num_cores
            
            self.cpus_counted.emit(actually_using)
            self.doMultiProcessing(actually_using)
        else:
            self.cpus_counted.emit(-1)
            self.doSerialProcessing()
        
            
    def doMultiProcessing(self,cores):
        global prepared_runs
        indices = range(len(prepared_runs))
        
        pool = mp.Pool(processes=cores)
        manager = mp.Manager()
        queue = manager.Queue()
        lock = manager.Lock()
        
        args = [(i,queue,lock) for i in indices]
        
        results = pool.map_async(worker, args)
        pool.close()
        while True:
            if results.ready():
                break
            else:
                size = queue.qsize()
                self.total_progress.emit(size,len(prepared_runs))
                sleep(1)
        
        hits = [x for x in results.get() if x == 1]
        self.success_ratio.emit(len(hits),len(prepared_runs))
        
        
    def doSerialProcessing(self):
        global prepared_runs
        global main_directory
        results = []
        for i,run in enumerate(prepared_runs):
            ret_code = compileRun(run,main_directory)
            results.append(ret_code)
            self.total_progress.emit(i+1,len(prepared_runs))

        hits = [x for x in results if x == 1]
        self.success_ratio.emit(len(hits),len(prepared_runs))
            
            
    def getIteratedRuns(self,iterator):
        # if this iterator has no run nested inside it,
        # then don't waste your time processing it
        if not iterator.getMyRun():
            return []
        
        #random.seed(iterator.getMyRun().getValueOf('seed'))
        
        # flush any previous overrides from this run (if any)
        iterator.getMyRun().clearRunOverrides()
        # note: the total number of runs generated will be the
        # product of the 'repeat' variable at each level
        # eg. if you have an outer iterator with 5 reps,
        #     and an inner with 3 reps, you get a total of
        #     5 x 3 = 15 individual runs.
        #
        # use itertools product to compute these as follows
        # create 2 data structures: one holds the display (form)name of the variable,
        # and the other holds the iterated values of that variable...so in the
        # 5x3 example above, with two variables epsilon and momentum, we might have
        # the following:
        # all_variables       all_values
        #      [ epsilon,   | [ v1,v2,v3,v4,v5 ]
        #        momentum ] | [ v1,v2,v3 ]
        all_variables = []
        all_applied_paths = []
        all_values = []
        level = iterator
        # set decimal precision!
        decimal.getcontext().prec = 6
        
        while level.getClassName() == 'MikenetIterator':
            # what are we varying?
            var_index = level.getValueOf('varying')
            var_name = level.getParameter('varying').dropdown_options[var_index]
            if var_name == '':
                # don't process blank level
                level = level.getChildren()[0]
            else:
                all_variables.append(var_name)
                all_applied_paths.append(level.getAppliedPaths())
                val = level.getValueOf('initial_value')
                delta = level.getValueOf('delta')
                level_values = []
                for i in range(level.getValueOf('repeat')):
                    if iterator.getRandomFlag():
                        arg1 = iterator.getRandomFlag()[1]
                        arg2 = iterator.getRandomFlag()[2]
                        if iterator.getRandomFlag()[0] == 'int':
                            level_values.append(random.randint(arg1,arg2))
                        elif iterator.getRandomFlag()[0] == 'double':
                            level_values.append(random.uniform(arg1,arg2))
                        elif iterator.getRandomFlag()[0] == 'gaussian':
                            level_values.append(random.gauss(arg1,arg2))
                    else:
                        level_values.append(val + (i * delta))
                    
                level_values = [decimal.Decimal(x) + decimal.Decimal(0) for x in level_values]
                level_values = [int(x) if x.as_tuple().exponent==0 else float(x) for x in level_values]
                all_values.append(level_values)
                level = level.getChildren()[0]
            
        # expand all_values using itertools product. returns a tuple for each run
        # of any override values
        iter_overrides = product(*all_values)

        # create the data structure to be returned
        iterated_runs = []

        for run_count,o in enumerate(iter_overrides):
            print 'overrides',o
            # first, make a copy the original run
            iterated_runs.append(iterator.getMyRun().getCopy())
            # change name to reflect iterator count
            base_name = iterated_runs[-1].getValueOf('run_name')
            iterated_runs[-1].getParameter('run_name').value = str(base_name+'_'+str(run_count+1))
            # next, add overrides
            for i,v in enumerate(all_variables):
                print 'iteratating over',v
                if v == 'Number of hidden units':
                    iterated_runs[-1].overrideParameter(v,(iterator.varying_parameter.value,o[i]),all_applied_paths[i])
                else:
                    print o[i]
                    iterated_runs[-1].overrideParameter(v,o[i],all_applied_paths[i])
        
        return iterated_runs

        
    def available_cpu_count(self):
        """From stackoverflow..."""

        # cpuset
        # cpuset may restrict the number of *available* processors
        try:
            m = re.search(r'(?m)^Cpus_allowed:\s*(.*)$',
                          open('/proc/self/status').read())
            if m:
                res = bin(int(m.group(1).replace(',', ''), 16)).count('1')
                if res > 0:
                    return res
        except IOError:
            pass

        # Python 2.6+
        try:
            return mp.cpu_count()
        except (ImportError, NotImplementedError):
            pass

        # http://code.google.com/p/psutil/
        try:
            import psutil
            return psutil.NUM_CPUS
        except (ImportError, AttributeError):
            pass

        # POSIX
        try:
            res = int(os.sysconf('SC_NPROCESSORS_ONLN'))

            if res > 0:
                return res
        except (AttributeError, ValueError):
            pass

        # Windows
        try:
            res = int(os.environ['NUMBER_OF_PROCESSORS'])

            if res > 0:
                return res
        except (KeyError, ValueError):
            pass

        # jython
        try:
            from java.lang import Runtime
            runtime = Runtime.getRuntime()
            res = runtime.availableProcessors()
            if res > 0:
                return res
        except ImportError:
            pass

        # BSD
        try:
            sysctl = subprocess.Popen(['sysctl', '-n', 'hw.ncpu'],
                                      stdout=subprocess.PIPE)
            scStdout = sysctl.communicate()[0]
            res = int(scStdout)

            if res > 0:
                return res
        except (OSError, ValueError):
            pass

        # Linux
        try:
            res = open('/proc/cpuinfo').read().count('processor\t:')

            if res > 0:
                return res
        except IOError:
            pass

        # Solaris
        try:
            pseudoDevices = os.listdir('/devices/pseudo/')
            res = 0
            for pd in pseudoDevices:
                if re.match(r'^cpuid@[0-9]+$', pd):
                    res += 1

            if res > 0:
                return res
        except OSError:
            pass

        # Other UNIXes (heuristic)
        try:
            try:
                dmesg = open('/var/run/dmesg.boot').read()
            except IOError:
                dmesgProcess = subprocess.Popen(['dmesg'], stdout=subprocess.PIPE)
                dmesg = dmesgProcess.communicate()[0]

            res = 0
            while '\ncpu' + str(res) + ':' in dmesg:
                res += 1

            if res > 0:
                return res
        except OSError:
            pass
        
        return None