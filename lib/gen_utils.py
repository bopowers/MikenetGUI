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
from random import sample

def evaluateEq(eq):
    '''Splits equation and returns tuple of left and right pieces.

    args:
    eq -- a string representation of an equation

    returns:
    (left side, ride side)

    White spaces are automatically removed from both sides.
    '''
    l,r = eq.split('=')
    l = l.strip()
    r = r.strip()
    return l,r

def smartEval(x):
    '''Tries to convert an arbitrary string into its most natural types.

    args:
    x -- input string

    returns:
    just about anything!
    
    Works like eval() except it doesn't break when given a string.

    Examples:
    "0.5" -> 0.5
    "banana" -> "banana"
    "['a','b']" -> ['a','b']
    '''
    try:
        y = eval(x)
        return y
    except:
        # probably a string, no need to convert
        return x

def moveInPlace(aList, fromIndex, toIndex):
    '''Move an item in an arbitrary list to a new position in that list.

    args:
    aList -- the list involved
    fromIndex -- the index where the item is first located
    toIndex -- the destination index

    Other items are shifted automatically. This function does not return
    a list, as it doesn't need to. It is designed to permanently
    alter the list in place. To undo, simply call with indices reversed.
    '''
    item = aList.pop(fromIndex)
    aList.insert(toIndex,item)

def getRandomString(length):
    chars = ['a','b','c','d','e','f','g','h','i','j',
             'k','l','m','n','o','p','q','r','s','t',
             'u','v','w','x','y','z',
             '0','1','2','3','4','5','6','7','8','9']
    aString = ''.join(sample(chars,length))
    return aString

def getUnusedName(base, existing_names):
    # this algorithm is ratchet.
    # sorting creates problems past 10, so 'numbers only' is a hack
    numbers_only = [int(x[len(base):]) for x in existing_names]
    i = 1
    for x in sorted(numbers_only):
        if i != x:
            break
        else:
            i += 1
    name_to_use = base + str(i)
    return name_to_use

def DFS_deTab(node):
    for child in node.getChildren():
        if child.getTabWidget():
            child.getGUI().unRegisterTabbedObject(child)
        DFS_deTab(child)


    
    
