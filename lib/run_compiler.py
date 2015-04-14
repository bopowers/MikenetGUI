import os
import db_utils
from shutil import copy, rmtree
import subprocess
import tarfile
import gzip
import sys, traceback
import time
import dialogs
import glob

def compileRun(run,mainDir):
    script_name = run.getGUI().getScript().getValueOf('script_name')
    run_name = run.getValueOf('run_name')

    # run path
    runPath = os.path.join(script_name,run_name)
    
    # try to make a new directory. returns an error if dir already exists
    # so if error is raised, delete the old and remake it
    try:
        os.makedirs(os.path.join(mainDir,"data",runPath))
    except:
        rmtree(os.path.join(mainDir,"data",runPath))
        os.mkdir(os.path.join(mainDir,"data",runPath))
            
    # before building run, copy templates into the new directory. don't modify originals
    copy(os.path.join(mainDir,"resources","template_code","mikenet_master.c"),
         os.path.join(mainDir,"data",runPath))
    copy(os.path.join(mainDir,"resources","template_code","build_model.c"),
         os.path.join(mainDir,"data",runPath))
    copy(os.path.join(mainDir,"resources","template_code","build_model.h"),
         os.path.join(mainDir,"data",runPath))
    # using make or scons?
    if run.getGUI().parameters['build_method'].value == 0:
        # scons
        copy(os.path.join(mainDir,"resources","template_code","SConstruct"),
             os.path.join(mainDir,"data",runPath))
    else:
        # make
        copy(os.path.join(mainDir,"resources","template_code","Makefile"),
             os.path.join(mainDir,"data",runPath))
            
    # switch to the newly created directory
    os.chdir(os.path.join(mainDir,'data',runPath))

    # scan through our copy of the build_model.c
    #
    # this process involves locating flags in the code template, and then replacing
    # each flag with a block of code. the code will define the following:
    #    includes, network architecture, phase structure, training and test set parameters
    
    with open('build_model.c','r') as build_file:
        build_lines = build_file.readlines()
        build_lines = [x.replace('\r','') for x in build_lines]
        # add test file path as an include at INCLUDE marker
        # this function also automatically copies the test file and all its includes
        # into the cwd
        build_lines = handleIncludes(run,build_lines)
        if not build_lines:
            # there was a fatal error, quit
            backToHomeDir()
            return 0
        
        # replace CONSTANTS marker with actual code
        build_lines = writeConstants(run,build_lines)
        if not build_lines:
            # there was a fatal error, quit
            backToHomeDir()
            return 0
        
        # replace BUILD_TESTS marker with actual code
        build_lines = writeTests(run,build_lines)
        if not build_lines:
            # there was a fatal error, quit
            backToHomeDir()
            return 0
        
        # replace BUILD_MAIN_NET marker with actual code
        # also get connection maps for building phase item nets
        build_lines, conn_map, bias_conn_map = writeNetBuild(run,build_lines)
        if not build_lines:
            # there was a fatal error, quit
            backToHomeDir()
            return 0

        # replace BUILD_PHASES marker with actual code
        build_lines = writePhases(run,build_lines)
        if not build_lines:
            # there was a fatal error, quit
            backToHomeDir()
            return 0
            
        # now for the training parameters...
        # replace the BUILD_PHASE_ITEMS flag...
        # build each phase item one at a time
        marker = [i for i,x in enumerate(build_lines) 
                  if 'INSERT_FLAG_BUILD_PHASE_ITEMS' in x]
        if not marker:
            print 'ERROR: No BUILD_PHASE_ITEMS flag found in template build_model.c file. Aborting run.'
            return 0
        # create the text_block to be inserted at build_lines[marker[0]]
        text_block = ''
        phase_count = 0
        phase_item_count = 0
        for phase in run.getChildren():
            for phase_item in phase.getChildren():
                text_block += writePhaseItem(phase_item,phase_count,
                                                     phase_item_count,conn_map,
                                                     bias_conn_map)
                phase_item_count += 1
                text_block += '\n'
            phase_count += 1
        
        # finally, indent all lines
        lines_to_indent = text_block.split('\n')
        lines_to_indent = [str('\t'+x) for x in lines_to_indent]
        text_block = '\n'.join(lines_to_indent)
        # replace marker line with actual variables
        build_lines[marker[0]] = text_block
        
    with open('build_model.c','w') as build_file:
        for line in build_lines:
            build_file.write(line)
            
    # before compiling, create a metadata file and put the top header info there
    # we're going to fill this file up with all parameters involved...it will go into
    # the metadata table of the database. if compiling is not successful, you can check
    # the metadata file for clues
    t_struct = time.localtime(time.time())
    start_date_str = str(t_struct[1])+'-'+str(t_struct[2])+'-'+str(t_struct[0])
    with open(run_name + '.metadata','w') as meta:
        # write parameters in a table format that will be loaded into the database later
        for ph in run.getChildren():
            for ph_item in ph.getChildren():
                meta.write('run_name=' + run_name + '\t')
                meta.write('start_date=' + start_date_str +'\t')
                if 'Random seed' in run.getRunOverrides():
                    meta.write('seed='+str(run.getRunOverrides()['Random seed']) + '\t')
                else:
                    meta.write('seed=' + str(run.getValueOf('seed')) + '\t')
                if 'Bias value' in run.getRunOverrides():
                    meta.write('bias_value='+str(run.getRunOverrides()['Bias value']) + '\t')
                else:
                    meta.write('bias_value=' + str(run.getValueOf('bias_value')) + '\t')
                if 'Weight range' in run.getRunOverrides():
                    meta.write('weight_range='+str(run.getRunOverrides()['Weight range']) + '\t')
                else:
                    meta.write('weight_range=' + str(run.getValueOf('weight_range')) + '\t')
                
                meta.write('phase_item=' + ph_item.getValueOf('item_name') + '\t')
                for pip in ph_item.getPrintableParameters('','\t'):
                    meta.write(pip)
                meta.write('\n')
                # start a new line and write network components
                groups = [x for x in run.getGroups() 
                          if x['name'] in ph_item.getComponentGroups()]
                for g in groups:
                    meta.write("GROUP\t")
                    meta.write('phase_item=' + ph_item.getValueOf('item_name') + '\t')
                    meta.write('group=' + g['name'] + '\t')
                    if ('Number of hidden units' in run.getRunOverrides()) and \
                        (g['name'] == run.getRunOverrides()['Number of hidden units'][0]):
                        meta.write('units=' + str(int(run.getRunOverrides()['Number of hidden units'][1]))+ '\t')
                    else:
                        meta.write('units=' + str(g['units']) + '\t')
                    meta.write('activation_type=' + g['activation_type'] + '\t')
                    meta.write('error_computation_type=' + 
                                g['error_computation_type'] + '\t')
                    meta.write('\n')
    
    # build it
    # using make or scons?
    if run.getGUI().parameters['build_method'].value == 0:
        # scons
        subprocess.call('scons',shell=True)
    else:
        # make
        subprocess.call('make mikenet_master',shell=True)
    
    # see if the build was successful
    if not os.path.isfile('mikenet_master.exe') and not os.path.isfile('mikenet_master'):
        print 'ERROR: Compiler encountered errors. Run was not built successfully.'
        return 0
    
    # run it
    if sys.platform == 'win32':
        # windows
        process = subprocess.Popen(['mikenet_master'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout,stderr = process.communicate()
        
        with open(str(run_name+'.log'),'w') as logFile:
            logFile.writelines(stdout)
            if stderr:
                logFile.write('*'*15+' stderr '+'*'*15+'\n')
                logFile.writelines(stderr)
    else:
        # unix flavored
        #subprocess.check_call(str("nohup nice -n9 ./mikenet_master > "+run_name+".log"),shell=True)
        process = subprocess.Popen(['nohup','nice','-n9','time','./mikenet_master','&'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout,stderr = process.communicate()
        
        with open(str(run_name+'.log'),'w') as logFile:
            logFile.writelines(stdout)
            if stderr:
                logFile.write('*'*15+' stderr '+'*'*15+'\n')
                logFile.writelines(stderr)
                
    # update database if one is specified
    if run.getGUI().parameters['use_database'] == 1:
        print 'Database gonna get made'
        db_utils.pushRunData(os.path.join(mainDir,'data',runPath),run.getGUI())
    
    # finally, zip all big files 
    for ex in ['*.activations','*.test','*.weights']:
    	for zipthis in glob.iglob(ex):
        	f_in = open(zipthis,'rb')
        	f_out = gzip.open((zipthis+'.gz'),'wb')
        	f_out.writelines(f_in)
        	f_out.close()
        	f_in.close()
        	# remove the old one
        	os.remove(zipthis)
        
    # AND tar/gzip the run directory
    os.chdir(os.pardir)
    with tarfile.open((run_name + '.tar.gz'),'w:gz') as tar:
        tar.add(run_name)
    rmtree(os.path.join(mainDir,"data",runPath))
    os.chdir(os.pardir)
    os.chdir(os.pardir)
   
    return 1

###################################################################################
# The following functions are helper functions for the compileRun method

def backToHomeDir():
    # these three lines get you back to the original working directory
    os.chdir(os.pardir) 
    os.chdir(os.pardir) 
    os.chdir(os.pardir)
    
def handleIncludes(run,build_lines):
    marker = [i for i,x in enumerate(build_lines) 
              if 'INSERT_FLAG_INCLUDES' in x]
    if not marker:
        print 'ERROR: No INCLUDES flag found in template build_model.c file. Aborting run.'
        return None
    # create the text_block to be inserted at build_lines[marker[0]]
    text_block = ''
    ##########################################################################
    # currently, only a single external test function is supported
    #
    # this code will check the user-defined test sets to make sure that only one
    # test file path is specified. It returns None if more than one test file is found
    func_path = []
    for test_profile in run.getGUI().getScript().getTestProfiles().getChildren():
        func_path.append(test_profile.getValueOf('function_path'))
    func_path = list(set(func_path))
    if len(func_path) == 0:
        # no test functions defined, return with no includes
        return build_lines
    if len(func_path) > 1:
        print 'ERROR: Function path unresolvable. Use only one test path per script.'
        return None
    if not os.path.isfile(func_path[0]):
        print 'ERROR: Cannot resolve path to',func_path[0]
        return None
    # we're all good...
    text_block += str('#include "' + func_path[0] + '"\n')
    
    ##########################################################################   
    # replace marker line with actual variables
    build_lines[marker[0]] = text_block
    return build_lines
    
def writeConstants(run,build_lines):
    marker = [i for i,x in enumerate(build_lines) 
              if 'INSERT_FLAG_CONSTANTS' in x]
    if not marker:
        print 'ERROR: No CONSTANTS flag found in template build_model.c file. Aborting run.'
        return None
    # create the text_block to be inserted at build_lines[marker[0]]
    text_block = ''
    ##########################################################################
    # how many test sets are there in all?
    text_block += ("#define NUM_TEST_SETS " + 
               str(len(run.getGUI().getScript().getTestProfiles().getChildren())) + "\n")
    # how many phases are there?
    text_block += ("#define NUM_PHASES " + str(len(run.getChildren())) + "\n")
    # how many phase items?
    pi_count = 0
    for phase in run.getChildren():
        pi_count += len(phase.getChildren())
    if pi_count == 0:
        print 'ERROR: There are no train or test events specified. Nothing to run.'
        return None
    text_block += ("#define NUM_PHASE_ITEMS " + str(pi_count) + "\n")
    text_block += ("#define TIME " +
                         str(run.getValueOf('ticks')) + "\n")
    # is seed overriden by iterator?
    if 'Random seed' in run.getRunOverrides():
        seed_const = run.getRunOverrides()['Random seed']
    else:
        seed_const = run.getValueOf('seed')
    text_block += ("#define SEED " +
                         str(seed_const) + "\n")
    # is weight range overriden by iterator?
    if 'Weight range' in run.getRunOverrides():
        range_const = run.getRunOverrides()['Weight range']
    else:
        range_const = run.getValueOf('weight_range')
    text_block += ("#define WEIGHT_RANGE " +
                         str(range_const) + "\n")
    text_block += ('char run_name[]="' + run.getValueOf('run_name') + '";\n')

    ##########################################################################   
    # replace marker line with actual variables
    build_lines[marker[0]] = text_block
    return build_lines
    
def writeTests(run,build_lines):
    marker = [i for i,x in enumerate(build_lines) 
              if 'INSERT_FLAG_BUILD_TESTS' in x]
    if not marker:
        print 'ERROR: No BUILD_TESTS flag found in template build_model.c file. Aborting run.'
        return None
    # create the text_block to be inserted at build_lines[marker[0]]
    text_block = ''
    ##########################################################################
    for i,profile in enumerate(run.getGUI().getScript().getTestProfiles().getChildren()):
        # initialize and allocate memory
        text_block += str('test_sets[' + str(i) + 
                          ']=(TestSet *)mh_calloc(sizeof(TestSet),1);\n')
        # test name
        name = profile.getValueOf('profile_name')
        text_block += str('test_sets[' + str(i) + ']->test_name=(char *)mh_malloc(' +
                                     str(len(name) + 1) + ');\n')
        text_block += str('test_sets[' + str(i) + ']->test_name="' + name + '";\n')
        # example set
        text_block += str('test_sets[' + str(i) + ']->test_examples=load_examples("' +
                          profile.getValueOf('example_path') + '",TIME);\n')
        # args
        # have to split apart the args
        arg_list = profile.getValueOf('args').split()
        text_block += str('test_sets[' + str(i) +
                          ']->args=(char **)mh_calloc(' +
                          str(len(arg_list)) + ',sizeof(char*));\n')
        for j,a in enumerate(arg_list):
            text_block += str('test_sets[' + str(i) +
                              ']->args[' + str(j) +
                              ']=(char *)mh_calloc(' + str(len(a)+1) +
                              ',sizeof(char));\n')
        for j,a in enumerate(arg_list):
            text_block += str('test_sets[' + str(i) +
                              ']->args[' + str(j) +
                              ']="' + a + '";\n')
        text_block += '\n'
    ##########################################################################   
    # replace marker line with actual variables
    build_lines[marker[0]] = text_block
    return build_lines

def writeNetBuild(run,build_lines):
    marker = [i for i,x in enumerate(build_lines) 
              if 'INSERT_FLAG_BUILD_MAIN_NET' in x]
    if not marker:
        print 'ERROR: No BUILD_MAIN_NET flag found in template build_model.c file. Aborting run.'
        return None,None,None
    # create the text_block to be inserted at build_lines[marker[0]]
    text_block = ''
    ##########################################################################
    # initialize group pointers
    text_block += 'Group'
    for i,g in enumerate(run.getGroups()):
        if i == 0:
            text_block += str(' *' + 'g' + str(i+1))
        else:
            text_block += str(', *' + 'g' + str(i+1))
    text_block += ', *bias;\n'
    # initialize connection pointers AND create connection maps to reference later
    connection_map = {}
    bias_connection_map = {}
    connection_count = 0
    text_block += 'Connections'
    matrix = run.getMatrix()
    for i in range(len(run.getGroups())):
        for j in range(len(run.getGroups())):
            if matrix[i][j] == 1:
                connection_count += 1
                name = str('c'+str(connection_count))
                connection_map[(i,j)] = name
                if connection_count == 1:
                    text_block += str(' *' + name)
                else:
                    text_block += str(', *' + name)
    # don't forget bias connections
    for j in range(len(run.getGroups())):
        if matrix[len(run.getGroups())][j] == 1:
            connection_count += 1
            name = str('c'+str(connection_count))
            bias_connection_map[j] = name
            if connection_count == 1:
                text_block += str(' *' + name)
            else:
                text_block += str(', *' + name)
            
    text_block += ';\n\n'
    # instantiate groups
    # first check if any of the groups' hidden units are overriden by an iterator
    override_group = [None,None]
    if 'Number of hidden units' in run.getRunOverrides():
        for g in run.getGroups():
            if g['name'] == run.getRunOverrides()['Number of hidden units'][0]:
                override_group[0] = g['name']
                override_group[1] = int(run.getRunOverrides()['Number of hidden units'][1])

    text_block += '/* create all groups. \n' 
    text_block += '   format is: name, num of units,  ticks */ \n'
    for i,g in enumerate(run.getGroups()):
        if g['name'] == override_group[0]:
            text_block += str('g' + str(i+1) + '=init_group("' +
                         g['name'] + '",' + str(override_group[1]) +
                         ',TIME);\n')
        else:
            text_block += str('g' + str(i+1) + '=init_group("' +
                         g['name'] + '",' + str(g['units']) +
                         ',TIME);\n')
        text_block += str('g' + str(i+1) + '->activationType=' +
                         g['activation_type'] + ';\n')
        text_block += str('g' + str(i+1) + '->errorComputation=' +
                         g['error_computation_type'] + ';\n')
    # and the bias
    # is bias overriden by iterator?
    if 'Bias value' in run.getRunOverrides():
        bias_val = run.getRunOverrides()['Bias value']
    else:
        bias_val = run.getValueOf('bias_value')
    text_block += str('bias=init_bias(' + str(bias_val) + ',TIME);\n')
    # bind groups to net
    text_block += '\n/* now add our groups to the run network object */ \n' 
    for i,g in enumerate(run.getGroups()):
        text_block += str('bind_group_to_net(run_net,' + 'g' + str(i+1) + ');\n')
    text_block += 'bind_group_to_net(run_net,bias);\n'

    # instantiate connections
    text_block += '\n/* now instantiate connection objects */ \n' 
    for k,v in connection_map.iteritems():
        i,j = k
        text_block += str(v + '=connect_groups(g' +
                         str(i+1) + ',g' + str(j+1) + ');\n')
        
    for k,v in bias_connection_map.iteritems():
        text_block += str(v + '=connect_groups(bias,' +
                         'g' + str(k+1) + ');\n')
    # bind connections to net
    text_block += '\n/* add connections to run network */ \n'
    for v in connection_map.values() + bias_connection_map.values():
        text_block += str('bind_connection_to_net(run_net,' +
                         v + ');\n')
    # randomize
    text_block += '\n/* randomize the weights in the connection objects. \n'
    text_block += '     2nd argument is weight range. */ \n'
    for v in connection_map.values() + bias_connection_map.values():
        text_block += str('randomize_connections(' +
                         v + ',WEIGHT_RANGE);\n')
    
    # finally, indent all lines
    lines_to_indent = text_block.split('\n')
    lines_to_indent = [str('\t'+x) for x in lines_to_indent]
    text_block = '\n'.join(lines_to_indent)

    ##########################################################################
    # replace marker line with actual variables
    build_lines[marker[0]] = text_block
    return build_lines, connection_map, bias_connection_map

def writePhaseItem(phase_item,phase_index,item_index,conn_map,bias_conn_map):
    text_block = ''
    text_block += str('/* phase item ' + str(item_index+1) + ': */ \n')
    # build subnetwork for this phase item
    # run groups for referencing group indices:
    run_groups = [x['name'] for x in phase_item.parent.parent.getGroups()]
    net_name = str('net' + str(item_index+1))
    
    text_block += str('Net *' + net_name + ';\n')
    text_block += str(net_name + '=create_net(TIME);\n')
    for group in phase_item.getComponentGroups():
        if group in run_groups:
            text_block += str('bind_group_to_net(' + net_name +
                              ',find_group_by_name("' + group +'"));\n')
    text_block += str('bind_group_to_net(' + net_name + ',bias);\n')
    # this is where we need connection maps...
    # because there is no "find connection by name" method
    for conn in phase_item.getComponentConnections():
        g_from,g_to = conn.split('%')
        if g_from in run_groups:
            if g_to in run_groups:
                from_i = run_groups.index(str(g_from))
                to_i = run_groups.index(str(g_to))
                c = conn_map[(from_i,to_i)]
                text_block += str('bind_connection_to_net(' + net_name +
                                  ',' + c + ');\n')
    for k,v in bias_conn_map.iteritems():
        if run_groups[k] in phase_item.getComponentGroups():
            text_block += str('bind_connection_to_net(' + net_name +
                                                  ',' + v + ');\n')
    # initialize new phase item
    text_block += str('phase_items[' + str(item_index) + 
                      ']=(PhaseItem *)mh_calloc(sizeof(PhaseItem),1);\n')
    # add subnetwork
    text_block += str('phase_items[' + str(item_index) + ']->net=' + net_name + ';\n')
    # item name
    name = phase_item.getValueOf('item_name')
    text_block += str('phase_items[' + str(item_index) + 
                      ']->item_name=(char *)mh_malloc(' + str(len(name) + 1) + ');\n')
    text_block += str('phase_items[' + str(item_index) + ']->item_name="' + name + '";\n')
    # which phase?
    text_block += str('phase_items[' + str(item_index) + ']->which_phase=' +
                      str(phase_index) + ';\n')
    # test only?
    if phase_item.getMode() == 'TRAIN':
            text_block += str('phase_items[' + str(item_index) + ']->test_only=0;\n')
    else:
            text_block += str('phase_items[' + str(item_index) + ']->test_only=1;\n')
    # test set indices and num tests
    # how many tests does this phase item have?
    my_tests = [i for i,x in 
                enumerate(phase_item.getGUI().getScript().getTestProfiles().getChildren())
                if x.getValueOf('profile_name') in phase_item.getTestProfiles()]
    text_block += str('phase_items[' + str(item_index) + ']->num_tests=' +
                      str(len(my_tests)) + ';\n')
    if len(my_tests) > 0:
        text_block += str('phase_items[' + str(item_index) + 
                ']->test_indices=(int *)mh_calloc(' + str(len(my_tests)) + ',sizeof(int));\n')
        for i,t in enumerate(my_tests):
            text_block += str('phase_items[' + str(item_index) + ']->test_indices[' +
                              str(i) + ']=' + str(t) + ';\n')

    # probability
    text_block += str('phase_items[' + str(item_index) + ']->probability=' +
                      str(phase_item.getValueOf('probability')) + ';\n')
    # total group readouts
    g_readouts = phase_item.getGroupReadouts()
    # (filter for only groups included in this phase item)
    g_readouts = [x for x in g_readouts if x in phase_item.getComponentGroups()]
    text_block += str('phase_items[' + str(item_index) + ']->total_group_readouts=' +
                      str(len(g_readouts)) + ';\n')
    if len(g_readouts) > 0:
        # all of the following is specifically for saving activation data
        # group readout names
        text_block += str('phase_items[' + str(item_index) +
                          ']->group_readout_names=(char **)mh_calloc(' +
                          str(len(g_readouts)) + ',sizeof(char*));\n')
        for i,g_ro in enumerate(g_readouts):
            text_block += str('phase_items[' + str(item_index) +
                              ']->group_readout_names[' + str(i) +
                              ']=(char *)mh_calloc(' + str(len(g_ro)+1) +
                              ',sizeof(char));\n')
        for i,g_ro in enumerate(g_readouts):
            text_block += str('phase_items[' + str(item_index) +
                              ']->group_readout_names[' + str(i) +
                              ']="' + g_ro + '";\n')
        # group readout times
        slices = phase_item.getAllRecordingTimes()
        text_block += str('phase_items[' + str(item_index) +
                          ']->group_readout_times=(int *)mh_calloc(' +
                          str(len(slices)) + ',sizeof(int));\n')
        for i,t in enumerate(slices):
            text_block += str('phase_items[' + str(item_index) +
                              ']->group_readout_times[' + str(i) +
                              ']=' + str(t) + ';\n')
        # readout table
        text_block += str('int roTable' + str(item_index) + '[' +
                          str(len(g_readouts)) + '][TIME]={\n')
        ro_table = phase_item.getSlicesByGroup()
        for g_ro in range(len(g_readouts)):
            text_block += '{'
            for t in range(len(ro_table[0])):
                text_block += str(ro_table[g_ro][t])
                if t == len(ro_table[0])-1:
                    text_block += '},\n'
                else:
                    text_block += ','
        text_block += '};\n'
        text_block += str('phase_items[' + str(item_index) +
                          ']->readout_table=(int **)mh_calloc(' +
                          str(len(g_readouts)) + ',sizeof(int*));\n')
        for i,g_ro in enumerate(g_readouts):
            text_block += str('phase_items[' + str(item_index) +
                              ']->readout_table[' + str(i) +
                              ']=(int *)mh_calloc(TIME,sizeof(int));\n')
        text_block += str('for(p=0;p<' + str(len(g_readouts)) +
                          ';p++) {\n\tfor(q=0;q<TIME;q++) {\n\t\t')
        text_block += str('phase_items[' + str(item_index) +
                          ']->readout_table[p][q]=roTable' + str(item_index) +
                          '[p][q];\n\t}\n}\n')
    
    # noise parameters....
    #  first, activation noise
    noise_data = [(k,v) for (k,v) in phase_item.getActivationNoiseData().iteritems() if
                  k in phase_item.getComponentGroups()]
    # also look in run overrides to see if you are iterating over noise values...these
    # take precendence over manually set noise values
    iter_noise_data = [(x,y) for (x,y) in phase_item.parent.parent.getRunOverrides().iteritems()
                       if 'Activation noise on' in x]
    iter_noise_data = [(x,y) for (x,y) in iter_noise_data if x[20:] in phase_item.getComponentGroups()]
    # make sure noise is actually overriden on THIS event
    for k,v in iter_noise_data:
        aps = phase_item.parent.parent.override_paths[k]
        if aps == 'ALL':
            # is this group already in noise_data?
            y = [i for i,x in enumerate(noise_data) if x[0] == k[20:]]
            if y:
                noise_data[y[0]] = (k[20:],v)
            else:
                noise_data.append((k[20:],v))
                
        else:
            aps = [x for x in aps if (x.split(':')[0] == phase_item.parent.getValueOf('phase_name'))\
                           and (x.split(':')[1] == phase_item.getValueOf('item_name'))]
            if aps:
                # is this group already in noise_data?
                y = [i for i,x in enumerate(noise_data) if x[0] == k[20:]]
                if y:
                    noise_data[y[0]] = (k[20:],v)
                else:
                    noise_data.append((k[20:],v))

    text_block += str('phase_items[' + str(item_index) + ']->total_activation_noise=' + 
                      str(len(noise_data)) + ';\n')
    if len(noise_data) > 0:
        # allocate memory for one array of values, and one of Groups
        text_block += str('phase_items[' + str(item_index) +
                          ']->activation_noise_values=(Real *)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Real));\n')
        text_block += str('phase_items[' + str(item_index) +
                          ']->activation_noise_groups=(Group **)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Group*));\n')
        # activation noise will be applied somewhere
        for counter,(k,v) in enumerate(noise_data):
            text_block += str('phase_items[' + str(item_index) +
                          ']->activation_noise_groups[' + str(counter) +
                          ']=find_group_by_name("' + str(k) + '");\n')
            text_block += str('phase_items[' + str(item_index) +
                          ']->activation_noise_values[' + str(counter) +
                          ']=' + str(v) + ';\n')

    # then input noise
    noise_data = [(k,v) for (k,v) in phase_item.getInputNoiseData().iteritems() if
                  k in phase_item.getComponentGroups()]
    # also look in run overrides to see if you are iterating over noise values...these
    # take precendence over manually set noise values
    iter_noise_data = [(x,y) for (x,y) in phase_item.parent.parent.getRunOverrides().iteritems()
                       if 'Input noise on' in x]
    iter_noise_data = [(x,y) for (x,y) in iter_noise_data if x[15:] in phase_item.getComponentGroups()]
    # make sure noise is actually overriden on THIS event
    for k,v in iter_noise_data:
        aps = phase_item.parent.parent.override_paths[k]
        if aps == 'ALL':
            # is this group already in noise_data?
            y = [i for i,x in enumerate(noise_data) if x[0] == k[15:]]
            if y:
                noise_data[y[0]] = (k[15:],v)
            else:
                noise_data.append((k[15:],v))
                
        else:
            aps = [x for x in aps if (x.split(':')[0] == phase_item.parent.getValueOf('phase_name'))\
                           and (x.split(':')[1] == phase_item.getValueOf('item_name'))]
            if aps:
                # is this group already in noise_data?
                y = [i for i,x in enumerate(noise_data) if x[0] == k[15:]]
                if y:
                    noise_data[y[0]] = (k[15:],v)
                else:
                    noise_data.append((k[15:],v))
                    
    text_block += str('phase_items[' + str(item_index) + ']->total_input_noise=' + 
                      str(len(noise_data)) + ';\n')
    if len(noise_data) > 0:
        # allocate memory for one array of values, and one of Groups
        text_block += str('phase_items[' + str(item_index) +
                          ']->input_noise_values=(Real *)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Real));\n')
        text_block += str('phase_items[' + str(item_index) +
                          ']->input_noise_groups=(Group **)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Group*));\n')
        # input noise will be applied somewhere
        for counter,(k,v) in enumerate(noise_data):
            text_block += str('phase_items[' + str(item_index) +
                          ']->input_noise_groups[' + str(counter) +
                          ']=find_group_by_name("' + str(k) + '");\n')
            text_block += str('phase_items[' + str(item_index) +
                          ']->input_noise_values[' + str(counter) +
                          ']=' + str(v) + ';\n')
                          
    # finally, weight noise
    noise_data = [(k,v) for (k,v) in phase_item.getWeightNoiseData().iteritems() if
                  k in phase_item.getComponentConnections()]
    # also look in run overrides to see if you are iterating over noise values...these
    # take precendence over manually set noise values
    
    # additive iterated noise
    iter_noise_data = [(x,y) for (x,y) in phase_item.parent.parent.getRunOverrides().iteritems()
                       if 'Weight noise (additive) on' in x]
    iter_noise_data = [(x,y) for (x,y) in iter_noise_data 
                       if x[27:].replace('->','%') in phase_item.getComponentConnections()]

    # make sure noise is actually overriden on THIS event
    for k,v in iter_noise_data:
        aps = phase_item.parent.parent.override_paths[k]
        if aps == 'ALL':
            # is this connection already in noise_data?
            y = [i for i,x in enumerate(noise_data) if x[0] == k[27:].replace('->','%')]
            if y:
                noise_data[y[0]] = (k[27:].replace('->','%'),[1,v])
            else:
                noise_data.append((k[27:].replace('->','%'),[1,v]))
                
        else:
            aps = [x for x in aps if (x.split(':')[0] == phase_item.parent.getValueOf('phase_name'))\
                           and (x.split(':')[1] == phase_item.getValueOf('item_name'))]
            if aps:
                # is this connection already in noise_data?
                y = [i for i,x in enumerate(noise_data) if x[0] == k[27:].replace('->','%')]
                if y:
                    noise_data[y[0]] = (k[27:].replace('->','%'),[1,v])
                else:
                    noise_data.append((k[27:].replace('->','%'),[1,v]))
                    
    # multiplicative iterated noise
    iter_noise_data = [(x,y) for (x,y) in phase_item.parent.parent.getRunOverrides().iteritems()
                       if 'Weight noise (multiplicative) on' in x]
    iter_noise_data = [(x,y) for (x,y) in iter_noise_data 
                       if x[33:].replace('->','%') in phase_item.getComponentConnections()]

    # make sure noise is actually overriden on THIS event
    for k,v in iter_noise_data:
        aps = phase_item.parent.parent.override_paths[k]
        if aps == 'ALL':
            # is this connection already in noise_data?
            y = [i for i,x in enumerate(noise_data) if x[0] == k[33:].replace('->','%')]
            if y:
                noise_data[y[0]] = (k[33:].replace('->','%'),[2,v])
            else:
                noise_data.append((k[33:].replace('->','%'),[2,v]))
                
        else:
            aps = [x for x in aps if (x.split(':')[0] == phase_item.parent.getValueOf('phase_name'))\
                           and (x.split(':')[1] == phase_item.getValueOf('item_name'))]
            if aps:
                # is this connection already in noise_data?
                y = [i for i,x in enumerate(noise_data) if x[0] == k[33:].replace('->','%')]
                if y:
                    noise_data[y[0]] = (k[33:].replace('->','%'),[2,v])
                else:
                    noise_data.append((k[33:].replace('->','%'),[2,v]))                       
                
    text_block += str('phase_items[' + str(item_index) + ']->total_weight_noise=' + 
                      str(len(noise_data)) + ';\n')
    if len(noise_data) > 0:
        # allocate memory for one array of values, one of types, and one of Connections
        text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_values=(Real *)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Real));\n')
        text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_connections=(Connections **)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(Connections*));\n')
        text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_types=(int *)mh_calloc(' +
                    str(len(noise_data)) + ',sizeof(int));\n')
        # weight noise will be applied somewhere
        for counter,(k,v) in enumerate(noise_data):
            g_from,g_to = k.split('%')
            from_i = run_groups.index(str(g_from))
            to_i = run_groups.index(str(g_to))
            c = conn_map[(from_i,to_i)]
            text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_connections[' + str(counter) +
                          ']=' + c + ';\n')
            text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_types[' + str(counter) +
                          ']=' + str(int(v[0])) + ';\n')
            text_block += str('phase_items[' + str(item_index) +
                          ']->weight_noise_values[' + str(counter) +
                          ']=' + str(v[1]) + ';\n')
    
    # counters and error
    text_block += str('phase_items[' + str(item_index) + ']->iter=0;\n')
    text_block += str('phase_items[' + str(item_index) + ']->wcount=0;\n')
    text_block += str('phase_items[' + str(item_index) + ']->ecount=0;\n')
    text_block += str('phase_items[' + str(item_index) + ']->tcount=0;\n')
    text_block += str('phase_items[' + str(item_index) + ']->ocount=0;\n')
    text_block += str('phase_items[' + str(item_index) + ']->error=0.0;\n\n')
    
    
    # now use the phase_item's 'get printable parameters' method to get the rest
    prefix = 'phase_items[' + str(item_index) + ']->'
    for processed_line in phase_item.getPrintableParameters(prefix,';\n'):
        text_block += processed_line
    
    return text_block

def writePhases(run,build_lines):
    marker = [i for i,x in enumerate(build_lines) 
              if 'INSERT_FLAG_BUILD_PHASES' in x]
    if not marker:
        print 'ERROR: No BUILD_PHASES flag found in template build_model.c file. Aborting run.'
        return None
    # create the text_block to be inserted at build_lines[marker[0]]
    text_block = ''
    ##########################################################################
    for i,phase in enumerate(run.getChildren()):
        text_block += str('/* phase ' + str(i+1) + ': */ \n')
        text_block += str('phases[' + str(i) + ']=(Phase *)mh_calloc(sizeof(Phase),1);\n')
        name = phase.getValueOf('phase_name')
        text_block += str('phases[' + str(i) + ']->phase_name=(char *)mh_malloc(' +
                         str(len(name) + 1) + ');\n')
        text_block += str('phases[' + str(i) + ']->phase_name="' + name + '";\n')
        text_block += str('phases[' + str(i) + ']->phase_order=' + 
                         str(phase.getValueOf('phase_order')) + '; //0=seq, 1=prob\n')
        text_block += str('phases[' + str(i) + ']->num_phase_items=' + 
                         str(len(phase.getChildren())) + ';\n')
        text_block += str('phases[' + str(i) + ']->max_iterations=' + 
                         str(phase.getValueOf('max_iterations')) + ';\n')
                                             
    
    # finally, indent all lines
    lines_to_indent = text_block.split('\n')
    lines_to_indent = [str('\t'+x) for x in lines_to_indent]
    text_block = '\n'.join(lines_to_indent)

    ##########################################################################
    # replace marker line with actual variables
    build_lines[marker[0]] = text_block
    return build_lines
