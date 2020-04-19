#!/usr/bin/env python3

import sys
import json

N = chr(155) #'\n' #newline character constant
MAXLEN = 40
first_char = ord('1')
DEBUG = 'OFF' #debug ON / OFF
MAX_ITEMS = 8

class Batch:
    def __init__(self):
        self.batch = ''
        
    def add(self,s):
        self.batch += s  +N
        
    def adde(self,s):
        self.batch +="ECHO "+ s  +N
    
    def adden(self,s):
        self.batch +="ECHO /N "+ s  +N

    def addel(self,s):
        for line in self.long_string_splitter(s):
            self.adde(line)
    
    def save(self, fname):
        #write to SpartaDOS X 4.4+ batch file
        with open(fname+'.BAT', 'wb') as f:
            f.write(self.batch.encode('latin-1',errors='ignore'))

    def long_string_splitter(self,line):
        #ECHO does not work well with long (>MAXLEN chars) lines
        #cut lines to MAXLEN chars or less and on spaces to make it prettier
        #addditionally cuts lines on slash "/"
        start = 0
        result = []
        get_more = True
        while get_more:
            end = start + MAXLEN
            full = line[start:end]
            if '/' in full:
                    last_space = full.index('/')
            else:
                if end < len(line):
                    if ' ' in full:
                        last_space = full.rindex(' ')
                    else:
                        last_space = end
                else:
                    last_space = len(line)-start
                    get_more = False
            cut = line[start:start+last_space]
            if '/' in cut:
                sys.stderr.write('New lines too close: '+cut+'\n')
            result.append(cut)
            if cut[0:2].lower()=='on' or cut[0:2].lower()=='of':
                sys.stderr.write('Bad line start: '+cut+'\n')            
            start=start+last_space+1 #skipping space - it is substituted for creating new line

        return result
        

with open(sys.argv[1]) as json_file:
    j = json.load(json_file)

l10n = j['l10n']

items_to_take = [] #Vn
conditions = [] #Cn
results = [] #Rn
items_with_art = {}

def parse_start(r):
    b = Batch()
    b.adde (DEBUG)
    b.add ('POKE 82 0') #no margin
    b.add ('LOAD COMMAND.COM') #speed up
    b.add ('LOAD IF.COM')      #speed up
    b.add ('LOAD INKEY.COM')   #speed up
    b.add ('LOAD ELSE.COM')
    b.add ('LOAD GOSUB.COM')
    b.add ('LOAD RETURN.COM')
    b.add ('LOAD GOTO.COM')
    b.add ('LOAD COPY.COM')
    
    #inventory cleansing
    b.add ('SET V=X') 
    for item in items_to_take:
        b.add ('  SET V'+ str(items_to_take.index(item)))

    for item in r['exits']:
        b.add ('SET BATCH='+str(item['id'])+'.BAT')

    b.save(r['id'])


def parse_inventory(r):
    b = Batch()
    b.adde(DEBUG)
    b.add(':BEGIN')#outer loop
    b.add('CLS')
    loc = '>'+r['name']+'<'
    filler = '-'*((MAXLEN-len(loc))//2)
    loc = filler + loc + filler
    loc = loc[0:MAXLEN-1]
    b.adde(loc)
    
    b.adde('\\t') #empty line
    b.addel(r['desc'])
    b.adde('\\t') #empty line
    
    #How many items do you carry?
    #Extremely convoluted counting in Sparta batches
    max_items = 'X'+'X'*(MAX_ITEMS)   # one X-> empty. 9X --> FULL
    curr_items = MAX_ITEMS
    while curr_items:
        b.add('IF V=="'+max_items+'"')
        b.adden(l10n['have']+str(curr_items))
        b.add('ELSE')
        curr_items -= 1
        max_items = max_items[:-1]
    
    b.adden(l10n['have']+'NO')
    
    for i in range(MAX_ITEMS):
        b.add('FI')
    
    b.adde(l10n['things']+'\\n')
    
        
    for item in items_to_take:
        b.add('IF V' + str(items_to_take.index(item))+'==1')
        b.adde('> '+ item)
        b.add('FI')
    #actions display
    b.adde('\\n'+l10n['todo'])

    for item in r['actions']:
        b.adde(item['desc']) #keys are hardcoded and val take from JSON
  
    b.adde('\\n'+l10n['esc'])
    
    #wait for key
    b.add('INKEY %KEY')

    b.add('IF %KEY=="'+chr(27)+'"')
    b.add('  SET BATCH=%1')
    b.add('  EXIT')
    b.add('FI')
    
    #show "pictures" of items
    b.add('IF %KEY=="L"')
    act = r['actions'][1] #second action is Look At items
    b.addel(act['result']['desc'])
    i=0
    for item in items_to_take:
        if item in items_with_art:
            b.add(' IF V' + str(items_to_take.index(item))+'==1')
            b.add('  PAUSE')
            b.adde( '> '+ item)
            b.add('  COPY /Q '+items_with_art[item]+' CON:')
            b.add(' FI')
        i += 1
        
    b.add(' PAUSE')
    b.add('FI')
    
    b.add('IF %KEY=="0"')
    act = r['actions'][0] #first action is DROP EVERYTHING
    b.addel(act['result']['desc'])
    b.adde(l10n['sure'])
    b.add(" IF INKEY 'Y'")     #note apostrophes!!!
    #drop all items
    for item in items_to_take:
        i = str(items_to_take.index(item))
        b.add(' IF V' +i)
        b.add('  SET V' +i+ '=0')
        b.add(' FI')
    b.add(' SET V=X') 
    b.add(' FI') #"Y"
    b.add('FI')  #"0"


    b.add('GOTO BEGIN')
    
    
    b.save(str(r['id']))

def prepare_rooms(r):
    #make item name to symbolic variable 
    if 'items' in r:
        for item in r['items']:
            if 'take' in item:
                #add to items_to_take
                if item['name'] in items_to_take:
                    sys.stderr.write('Warning! "'+item['name'] + '" already in items_to_take.'+'\n')
                    continue
                else:
                    items_to_take.append(item['name'])
                    if 'art' in item:
                        items_with_art[item['name']] = item['art']
    
    if 'actions' in r:
        for action in r['actions']:
            if 'conditions' in action:
                for condition in action['conditions']:
                    # add conditions
                    if condition in conditions:
                        sys.stderr.write('Warning! "'+ condition + '" already in conditions.'+'\n')
                        continue
                    else:
                        conditions.append(condition)
            if 'result' in action and 'var' in action['result']:
                results.append(action['result']['var'])

    if 'exits' in r:
        for exit in r['exits']:
            if 'conditions' in exit:
                for condition in exit['conditions']:
                    # add conditions
                    if condition in conditions:
                        sys.stderr.write('Warning! "'+ condition + '" already in conditions.'+'\n')
                        continue
                    else:
                        conditions.append(condition)

            

    #now you can find index of an item with items_to_take.index("spoon") 
    #and name var V+index, e.g. V0, V1, etc
    
def parse_room_sparta(r):

    #init
    b = Batch()
    b.adde(DEBUG) #debug ON / OFF
    b.add ('POKE 82 0') #no margin
        
    b.add(':BEGIN') #outer loop
    b.add('CLS')
    #==========>Location: Bedroom<==========
    #loc = '>'+l10n['loc']+r['name']+'<'
    loc = '>'+r['name']+'<'
    filler = '='*((MAXLEN-len(loc))//2)
    loc = filler + loc + filler
    loc = loc[0:MAXLEN-1] 
    b.adde(loc)
    
    #picture
    if 'art' in r:
        b.add('COPY /Q '+r['art']+' CON:') #faster
        #b.add('TYPE '+r['art'])  #slower
    #description
    b.adde('\\t') #empty line
    if 'art-pause' in r:
        b.add('PAUSE')
    b.addel(r['desc'])
                    

    #----------------------------------------------------------
    #locations display
    #you see these items...:
    i = 0
    if 'items' in r:
        b.adde('\\n'+l10n['see'])
        for item in r['items']:
            if item['name'] in items_to_take:
                b.add('IF NOT V' + str(items_to_take.index(item['name'])))
            b.adde('<'+chr(i+first_char)+'> '+ item['name'])
            if item['name'] in items_to_take:
                b.add('FI')
            i += 1
    
    #actions display
    if 'actions' in r:
        b.adde('\\n'+l10n['todo'])
        for item in r['actions']:
            b.adde('<'+chr(i+first_char)+'> '+ item['desc'])
            i += 1

    if 'talk' in r:
        b.adde('\\n'+l10n['say'])
    else:
        b.adde('\\n'+l10n['goto'])

    for item in r['exits']:
        b.adde('<'+chr(i+first_char)+'> '+ item['desc'])
        i += 1
    
    #"menu"
    b.adde('\\n'+l10n['inv'])
    b.adden('\\n'+l10n['key']) #no going to the next line with \N

    #----------------------------------------------------------
    #locations and examine choice
    b.add('INKEY %KEY')
    b.add('ECHO \\t') #empty line
    i = 0
    
    if 'items' in r:
        for item in r['items']:
            if item['name'] in items_to_take:
                b.add('IF NOT V' + str(items_to_take.index(item['name'])))
            b.add(' IF %KEY=="'+chr(i+first_char)+'"')
            b.addel(item['desc']) #description
                
            if 'take' in item:
                b.adden(l10n['take'])
                b.add("  IF INKEY 'Y'")     #note apostrophes!!!
                b.add('    IF V=="'+'X'+'X'*(MAX_ITEMS)+'"')
                b.add('     ECHO \\n'+l10n['full'])
                b.add('    ELSE')
                b.add('     ECHO '+l10n['taken'])
                b.add('     SET V'+ str(items_to_take.index(item['name']))+'=1')
                b.add('     SET V=$V$X')
                if 'art' in item:
                    b.add('     COPY /Q '+item['art']+' CON:')
                b.add('    FI')
                b.add('  ELSE')
                b.add('    ECHO '+l10n['ntaken'])
                b.add('  FI')
                b.add('  SET %KEY')
            b.add('FI')
            if item['name'] in items_to_take:
                b.add('FI')
            i += 1
    
    if 'actions' in r:
        for item in r['actions']:
            b.add('IF %KEY=="'+chr(i+first_char)+'"')

            #opening IFs
            if 'conditions' in item:
                negation = False
                for condition in item['conditions']:
                    if condition[0] == '!': #negation!
                        negation = True
                        condition = condition[1:]
                    if not negation:
                        if condition in items_to_take: #you need a certain item to perform the action
                            b.add('IF V'+str(items_to_take.index(condition))+'==1')
                        elif condition in results:
                            b.add('IF R'+str(results.index(condition))+'==1')
                        elif condition=='nothing': #requires empty backpack
                            b.add('IF V=="X"')
                    else:
                        if condition in items_to_take: #item NEVER was in your backpack
                            b.add('IF NOT V'+str(items_to_take.index(condition)))
                        elif condition in results:
                            b.add('IF NOT R'+str(results.index(condition)))
            
            #all conditions met
            if 'result' in item:
                b.addel(item['result']['desc'])
            if 'art' in item:
                b.add('  COPY /Q '+item['art']+' CON:')
            #setting result
            if 'result' in item and 'var' in item['result']:
                b.add(' SET R'+str(results.index(item['result']['var']))+'=1')
            #using all items (deleting them)
            if 'conditions' in item:
                for condition in item['conditions']:
                    if condition in items_to_take: #you need a certain item to perform the action
                        b.add(' SET V'+str(items_to_take.index(condition))+'=0')
                        b.add(' GOSUB DEC_ITEMS')
                    

            #closing ELSE FI
            if 'conditions' in item:
                for condition in item['conditions']:
                    b.add('ELSE')
                    b.add(' ECHO '+l10n['cant'])
                    b.add('FI')
                    
            b.add('FI')
            i += 1
    
    for item in r['exits']:
        b.add('IF %KEY=="'+chr(i+first_char)+'"')
        #opening IFs
        if 'conditions' in item:
            negation = False
            for condition in item['conditions']:
                if condition[0] == '!': #negation!
                    negation = True
                    condition = condition[1:]
                if not negation:
                    if condition in items_to_take: #you need a certain item to perform the action
                        b.add('IF V'+str(items_to_take.index(condition))+'==1')
                    elif condition in results:
                        b.add('IF R'+str(results.index(condition))+'==1')
                    elif condition=='nothing': #requires empty backpack
                        b.add('IF V=="X"')
                else:
                    if condition in items_to_take: #item NEVER was in your backpack
                        b.add('IF NOT V'+str(items_to_take.index(condition)))
                    elif condition in results:
                        b.add('IF NOT R'+str(results.index(condition)))
        #all conditions met
        if 'art' in item:
            b.add('  COPY /Q '+item['art']+' CON:')
        b.add('  SET BATCH='+str(item['id'])+'.BAT')
        b.add('  EXIT')

        #closing ELSE FI
        if 'conditions' in item:
            for condition in item['conditions']:
                b.add('ELSE')
                b.add(' ECHO '+l10n['cant'])
                b.add('FI')

        b.add('FI')
        i += 1

    #call inventory
    b.add('IF %KEY=="I"')
    b.add('  SET BATCH=INV.BAT ' + str(r['id']) + '.BAT')
    b.add('  EXIT')
    b.add('FI')
    
    #quit to DOS
    b.add('IF %KEY=="Q"')
    b.adde(l10n['quit'])
    b.add(" IF INKEY 'Y'")     #note apostrophes!!!
    b.add('  LOAD') #clearing BATCH cache
    b.add('  CD ..') 
    b.add('  EXIT')
    b.add(' FI')
    b.add('FI')
    

    #return to main view on enter
    b.add('PAUSE')
    b.add('GOTO BEGIN')

    #----------------------------------------------------------
    # decrease number of items by 1
    if 'GOSUB DEC_ITEMS' in b.batch:
        b.add('PROC DEC_ITEMS')

        max_items = 'X'+'X'*(MAX_ITEMS)   # one X-> empty. 9X --> FULL
        curr_items = MAX_ITEMS
        while curr_items:
            b.add('IF V=="'+max_items+'"')
            max_items = max_items[:-1]
            b.add(' SET V='+max_items)
            b.add('ELSE')
            curr_items -= 1
        
        b.add('ECHO '+l10n['math_error'])
        for i in range(MAX_ITEMS):
            b.add('FI')
        
        b.add('RETURN')
    
    

    b.save(str(r['id']))

#----------------------------------------------------------
#parse rooms
#----------------------------------------------------------
for room in j['rooms']:
    prepare_rooms(room)

print('------------------')
print('Variables')
for item in items_to_take:
    print('V'+str(items_to_take.index(item)), item)
print('------------------')
print('Conditions')
for item in conditions:
    print('C'+str(conditions.index(item)), item)
print('------------------')
print('Results')
for item in results:
    print('R'+str(results.index(item)), item)

for room in j['rooms']:
    parse_room_sparta(room)

#parse inventory
parse_inventory(j['inventory'])

#parse start
parse_start(j['start'])


