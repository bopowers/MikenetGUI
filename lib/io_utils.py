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

import gen_utils as guts
from data_structures import *
from PySide import QtGui
import dialogs
import sys,traceback

gap = '\t'

# WRITE METHODS  ########################################################

def writeParameter(f,p,indent):
    new_indent = indent + gap
    f.write(indent + '<parameter>\n')
    f.write(new_indent + 'variable_name = ' + p.variable_name + ';\n')
    f.write(new_indent + 'widget_type = ' + p.widget_type + ';\n')
    f.write(new_indent + 'value = ' + str(p.value) + ';\n')
    f.write(new_indent + 'form_name = ' + p.form_name + ';\n')
    f.write(new_indent + 'override_flag = ' + str(p.override_flag) + ';\n')
    if p.comment:
        if type(p.comment) == str:
            f.write(new_indent + 'comment = ' + p.comment + ';\n')
    if p.minimum and p.maximum:
        f.write(new_indent + 'range = [' + str(p.minimum) + ',' +
                str(p.maximum) +'];\n')
    if p.step:
        f.write(new_indent + 'step = ' + str(p.step) + ';\n')
    if p.decimals:
        f.write(new_indent + 'decimals = ' + str(p.decimals) + ';\n')
    if p.category:
        f.write(new_indent + 'category = ' + p.category + ';\n')
    if p.dropdown_options:
        f.write(new_indent + 'dropdown_options = ' +
                str(p.dropdown_options) + ';\n')
    if p.override_flag == 1:
        f.write(new_indent + 'override_flag = ' +
                str(p.override_flag) + ';\n')
    if p.password_flag == 1:
        f.write(new_indent + 'password_flag = ' +
                str(p.password_flag) + ';\n')
    if p.extension:
        f.write(new_indent + 'extension = ' + str(p.extension) + ';\n')
    f.write(indent + '</parameter>\n')
    
def writeVaryingParameter(f,p,indent):
    new_indent = indent + gap
    f.write(indent + '<varying_parameter>\n')
    f.write(new_indent + 'variable_name = ' + p.variable_name + ';\n')
    f.write(new_indent + 'widget_type = ' + p.widget_type + ';\n')
    f.write(new_indent + 'value = ' + str(p.value) + ';\n')
    f.write(new_indent + 'form_name = ' + p.form_name + ';\n')
    f.write(new_indent + 'override_flag = ' + str(p.override_flag) + ';\n')
    if p.comment:
        if type(p.comment) == str:
            f.write(new_indent + 'comment = ' + p.comment + ';\n')
    if p.minimum and p.maximum:
        f.write(new_indent + 'range = [' + str(p.minimum) + ',' +
                str(p.maximum) +'];\n')
    if p.step:
        f.write(new_indent + 'step = ' + str(p.step) + ';\n')
    if p.decimals:
        f.write(new_indent + 'decimals = ' + str(p.decimals) + ';\n')
    if p.category:
        f.write(new_indent + 'category = ' + p.category + ';\n')
    if p.dropdown_options:
        f.write(new_indent + 'dropdown_options = ' +
                str(p.dropdown_options) + ';\n')
    if p.override_flag == 1:
        f.write(new_indent + 'override_flag = ' +
                str(p.override_flag) + ';\n')
    if p.password_flag == 1:
        f.write(new_indent + 'password_flag = ' +
                str(p.password_flag) + ';\n')
    if p.extension:
        f.write(new_indent + 'extension = ' + str(p.extension) + ';\n')
    f.write(indent + '</varying_parameter>\n')

def writePhaseItem(f,phase_item,indent):
    new_indent = indent + gap
    f.write(indent + '<phase_item>\n')
    f.write('\n')
    f.write(new_indent + 'my_profile = ' + phase_item.getProfile() + '\n')
    f.write(new_indent + 'mode = ' + phase_item.getMode() + '\n')
    f.write(new_indent + 'test_profiles = ' + str(phase_item.getTestProfiles()) + '\n')
    f.write('\n')
    for p in phase_item.parameters.values():
        writeParameter(f,p,new_indent)
        f.write('\n')
    # phase items have some special member data structures..write these here
    # overrides (these are just stripped down parameters)
    f.write('\n')
    f.write(new_indent + '<overrides>\n')
    for p in phase_item.getOverrides():
        writeParameter(f,p,new_indent+gap)
    f.write(new_indent + '</overrides>\n')
    f.write('\n')
    # recording data (this is a dict you can just write in its raw form)
    f.write(new_indent + 'recording_data = ' + str(phase_item.recording_data) + '\n')
    f.write('\n')
    # net components (this is also a dict you can write the same as recording data)
    f.write(new_indent + 'net_components = ' + str(phase_item.net_components) + '\n')
    f.write('\n')
    # noise data (same as recording and net component data)
    f.write(new_indent + 'noise_data = ' + str(phase_item.noise_data) + '\n')
    f.write('\n')
    f.write(indent + '</phase_item>\n')

def writePhase(f,phase,indent):
    new_indent = indent + gap
    f.write(indent + '<phase>\n')
    f.write('\n')
    for p in phase.parameters.values():
        writeParameter(f,p,new_indent)
        f.write('\n')
    for child in phase.getChildren():
        writePhaseItem(f,child,new_indent)
        f.write('\n')
    f.write(indent + '</phase>\n')

def writeRun(f,run,indent):
    new_indent = indent + gap
    f.write(indent + '<run>\n')
    f.write('\n')
    f.write(new_indent + 'groups = ' + str(run.groups) + '\n')
    f.write(new_indent + 'matrix = ' + str(run.adjacency_matrix) + '\n')
    for p in run.parameters.values():
        writeParameter(f,p,new_indent)
        f.write('\n')
    for child in run.getChildren():
        writePhase(f,child,new_indent)
        f.write('\n')
    f.write(indent + '</run>\n')

def writeIterator(f,iterator,indent):
    new_indent = indent + gap
    f.write(indent + '<iterator>\n')
    f.write('\n')
    f.write(new_indent + 'random_flag = ' + str(iterator.getRandomFlag()) + '\n')
    f.write('\n')
    f.write(new_indent + 'applied_paths = ' + str(iterator.getAppliedPaths()) + '\n')
    f.write('\n')
    # write varying parameter with a special tag
    writeVaryingParameter(f,iterator.varying_parameter,new_indent)
    f.write('\n')
    
    for p in iterator.parameters.values():
        writeParameter(f,p,new_indent)
        f.write('\n')
    for child in iterator.getChildren():
        if child.getClassName() == 'MikenetIterator':
            writeIterator(f,child,new_indent)
            f.write('\n')
        else:
            writeRun(f,child,new_indent)
            f.write('\n')
    f.write(indent + '</iterator>\n')
    
def writeTrainingProfile(f,profile,indent):
    new_indent = indent + gap
    f.write(indent + '<training_profile>\n')
    f.write('\n')
    f.write(new_indent + 'category_labels = ' + str(profile.category_labels) + '\n')
    for p in profile.getAllParameters():
        writeParameter(f,p,new_indent)
        f.write('\n')
    f.write(indent + '</training_profile>\n')
    
def writeTestProfile(f,profile,indent):
    new_indent = indent + gap
    f.write(indent + '<test_profile>\n')
    f.write('\n')
    for p in profile.getAllParameters():
        writeParameter(f,p,new_indent)
        f.write('\n')
    f.write(indent + '</test_profile>\n')

def writeScript(script,fname):
    with open(fname,'w') as f:
        f.write('<script>\n')
        f.write('\n')
        for d in script.getDefaults():
            f.write(gap + '&default& = ' + str(d) + '\n')
        for p in script.parameters.values():
            writeParameter(f,p,gap)
            f.write('\n')
        for profile in script.getTrainingProfiles().getChildren():
            writeTrainingProfile(f,profile,gap)
            f.write('\n')
        for profile in script.getTestProfiles().getChildren():
            writeTestProfile(f,profile,gap)
            f.write('\n')
        for child in script.getChildren():
            if child.getClassName() == 'MikenetIterator':
                writeIterator(f,child,gap)
                f.write('\n')
            else:
                writeRun(f,child,gap)
                f.write('\n')
        f.write('</script>\n')

# END WRITE METHODS   ###################################################

# BEGIN READ METHODS  ###################################################

def readParameter(lines,start_index,parent,gui):
    i = start_index
    paramDict = {}
    while '</parameter>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if r == ';':
                # must have been an empty text field
                paramDict[l] = ''
            else:
                r = r[:-1]
                paramDict[l] = guts.smartEval(r)
        i += 1
    if type(parent.parameters) == dict:
        name = paramDict['variable_name']
        parent.parameters[name] = MikenetParameter(gui,**paramDict)
    else:
        parent.parameters.append(MikenetParameter(gui,**paramDict))
    return i
        
def readParameterOverride(lines,start_index,o_list,gui):
    i = start_index
    paramDict = {}
    while '</parameter>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if r == ';':
                # must have been an empty text field
                paramDict[l] = ''
            else:
                r = r[:-1]
                paramDict[l] = guts.smartEval(r)
        i += 1
        
    o_list.append(MikenetParameter(gui,**paramDict))
    return i
    
def readVaryingParameter(lines,start_index,iterator,gui):
    '''special method for iterator's "varying" parameter'''
    i = start_index
    paramDict = {}
    while '</varying_parameter>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if r == ';':
                # must have been an empty text field
                paramDict[l] = ''
            else:
                r = r[:-1]
                paramDict[l] = guts.smartEval(r)
        i += 1
  
    iterator.setVarying(MikenetParameter(gui,**paramDict))
    return i
    
def readOverrides(lines,start_index,phase_item,gui):
    i = start_index
    while '</overrides>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameterOverride(lines,i+1,phase_item.getOverrides(),gui)
        i += 1
    return i
    
def readPhaseItem(lines,start_index,parent,gui):
    i = start_index
    phase_item = MikenetPhaseItem(gui,parent)
    #TODO read test sets
    while '</phase_item>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if l == 'my_profile':
                phase_item.setProfile(r)
            elif l == 'mode':
                phase_item.setModeWithText(r)
            elif l == 'recording_data':
                phase_item.setRawRecordingData(guts.smartEval(r))
            elif l == 'net_components':
                phase_item.setRawNetComponents(guts.smartEval(r))
            elif l == 'noise_data':
                phase_item.setRawNoiseData(guts.smartEval(r))
            elif l == 'test_profiles':
                phase_item.test_profiles = guts.smartEval(r)
                
        elif '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,phase_item,gui)
        
        elif '<overrides>' in lines[i]:
            i = readOverrides(lines,i+1,phase_item,gui)
            
        i += 1
    # add newly created phase item to phase
    parent.children.append(phase_item)
    phase_item.createTab()
    return i

def readPhase(lines,start_index,parent,gui):
    i = start_index
    phase = MikenetPhase(gui,parent)
    while '</phase>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,phase,gui)
        elif '<phase_item>' in lines[i]:
            i = readPhaseItem(lines,i+1,phase,gui)
        i += 1
    # add newly created phase to run
    parent.children.append(phase)
    return i

def readRun(lines,start_index,parent,gui):
    i = start_index
    run = MikenetRun(gui,parent)
    while '</run>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if l == 'groups':
                run.setGroups(guts.smartEval(r))
            elif l == 'matrix':
                run.setMatrix(guts.smartEval(r))
        elif '<phase>' in lines[i]:
            i = readPhase(lines,i+1,run,gui)
        elif '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,run,gui)
        i += 1
    # add newly created run to parent
    parent.children.append(run)
    run.createTab()
    # phases have special widgets instead of tabs
    # need to create these AFTER the run tab is made
    for phase in run.getChildren():
        phase.createWidget()
    return i

def readIterator(lines,start_index,parent,gui):
    i = start_index
    it = MikenetIterator(gui,parent)
    while '</iterator>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,it,gui)
            
        elif '<varying_parameter>' in lines[i]:
            i = readVaryingParameter(lines,i+1,it,gui)
            
        elif '<iterator>' in lines[i]:
            i = readIterator(lines,i+1,it,gui)
            
        elif '<run>' in lines[i]:
            i = readRun(lines,i+1,it,gui)

        elif 'random_flag' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            it.setRandomFlag(guts.smartEval(r))
            
        elif 'applied_paths' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            it.setAppliedPaths(guts.smartEval(r))

        i += 1
    # add newly created iterator to parent
    parent.getChildren().append(it)
    it.syncToRun()
    it.createTab()
    return i
    
def readTrainingProfile(lines,start_index,parent,gui):
    i = start_index
    prof = MikenetTrainingProfile(gui,parent)
    while '</training_profile>' not in lines[i]:
        if 'category_labels' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            prof.setCategories(guts.smartEval(r))
        elif '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,prof,gui)
        i += 1
    # add the newly created profile to the script
    parent.getChildren().append(prof)
    return i
        
def readTestProfile(lines,start_index,parent,gui):
    i = start_index
    prof = MikenetTestProfile(gui,parent)
    while '</test_profile>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,prof,gui)
        i += 1
    # add the newly created profile to the script
    parent.getChildren().append(prof)
    return i
            
def readScript(gui,fname):
    script = MikenetScript(gui)
    try:
        with open(fname,'r') as f:
            lines = f.readlines()
            # preprocess by removing empty lines and stripping whitespace
            lines = [x.strip() for x in lines if x != '\n']
            i = 0
            while '</script>' not in lines[i]:
                if '&default&' in lines[i]:
                    l,r = guts.evaluateEq(lines[i])
                    script.defaults.append(guts.smartEval(r))

                elif '<run>' in lines[i]:
                    i = readRun(lines,i+1,script,gui)
                    
                elif '<iterator>' in lines[i]:
                    i = readIterator(lines,i+1,script,gui)
                        
                elif '<parameter>' in lines[i]:
                    i = readParameter(lines,i+1,script,gui)
                    
                elif '<training_profile>' in lines[i]:
                    i = readTrainingProfile(lines,i+1,script.training_profiles,gui)
                    
                elif '<test_profile>' in lines[i]:
                    i = readTestProfile(lines,i+1,script.test_profiles,gui)

                i += 1

        script.createTab()
        return script
    except:
        dialogs.showError(gui,'There was a problem reading file '+fname+
                          '. Please check the file formatting and try again.','')
        traceback.print_exc(file=sys.stdout)
        return None

### CLI VERSIONS
    
def cli_readPhaseItem(lines,start_index,parent,gui):
    i = start_index
    phase_item = MikenetPhaseItem(gui,parent)
    #TODO read test sets
    while '</phase_item>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if l == 'my_profile':
                phase_item.setProfile(r)
            elif l == 'mode':
                phase_item.setModeWithText(r)
            elif l == 'recording_data':
                phase_item.setRawRecordingData(guts.smartEval(r))
            elif l == 'net_components':
                phase_item.setRawNetComponents(guts.smartEval(r))
            elif l == 'noise_data':
                phase_item.setRawNoiseData(guts.smartEval(r))
            elif l == 'test_profiles':
                phase_item.test_profiles = guts.smartEval(r)
                
        elif '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,phase_item,gui)
        
        elif '<overrides>' in lines[i]:
            i = readOverrides(lines,i+1,phase_item,gui)
            
        i += 1
    # add newly created phase item to phase
    parent.children.append(phase_item)
    return i

def cli_readPhase(lines,start_index,parent,gui):
    i = start_index
    phase = MikenetPhase(gui,parent)
    while '</phase>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,phase,gui)
        elif '<phase_item>' in lines[i]:
            i = cli_readPhaseItem(lines,i+1,phase,gui)
        i += 1
    # add newly created phase to run
    parent.children.append(phase)
    return i

def cli_readRun(lines,start_index,parent,gui):
    i = start_index
    run = MikenetRun(gui,parent)
    while '</run>' not in lines[i]:
        if '=' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            if l == 'groups':
                run.setGroups(guts.smartEval(r))
            elif l == 'matrix':
                run.setMatrix(guts.smartEval(r))
        elif '<phase>' in lines[i]:
            i = cli_readPhase(lines,i+1,run,gui)
        elif '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,run,gui)
        i += 1
    # add newly created run to parent
    parent.children.append(run)
    return i

def cli_readIterator(lines,start_index,parent,gui):
    i = start_index
    it = MikenetIterator(gui,parent)
    while '</iterator>' not in lines[i]:
        if '<parameter>' in lines[i]:
            i = readParameter(lines,i+1,it,gui)
            
        elif '<varying_parameter>' in lines[i]:
            i = readVaryingParameter(lines,i+1,it,gui)
            
        elif '<iterator>' in lines[i]:
            i = cli_readIterator(lines,i+1,it,gui)
            
        elif '<run>' in lines[i]:
            i = cli_readRun(lines,i+1,it,gui)

        elif 'random_flag' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            it.setRandomFlag(guts.smartEval(r))
            
        elif 'applied_paths' in lines[i]:
            l,r = guts.evaluateEq(lines[i])
            it.setAppliedPaths(guts.smartEval(r))

        i += 1
    # add newly created iterator to parent
    parent.getChildren().append(it)
    it.syncToRun()
    return i
            
def cli_readScript(gui,fname):
    script = MikenetScript(gui)
    try:
        with open(fname,'r') as f:
            lines = f.readlines()
            # preprocess by removing empty lines and stripping whitespace
            lines = [x.strip() for x in lines if x != '\n']
            i = 0
            while '</script>' not in lines[i]:
                if '&default&' in lines[i]:
                    l,r = guts.evaluateEq(lines[i])
                    script.defaults.append(guts.smartEval(r))

                elif '<run>' in lines[i]:
                    i = cli_readRun(lines,i+1,script,gui)
                    
                elif '<iterator>' in lines[i]:
                    i = cli_readIterator(lines,i+1,script,gui)
                        
                elif '<parameter>' in lines[i]:
                    i = readParameter(lines,i+1,script,gui)
                    
                elif '<training_profile>' in lines[i]:
                    i = readTrainingProfile(lines,i+1,script.training_profiles,gui)
                    
                elif '<test_profile>' in lines[i]:
                    i = readTestProfile(lines,i+1,script.test_profiles,gui)

                i += 1

        return script
    except:
        print str('There was a problem reading file '+fname+
                  '. Please check the file formatting and try again.')
        traceback.print_exc(file=sys.stdout)
        sys.exit(0)
        

