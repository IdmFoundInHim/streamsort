# StreamSort ©2019 IdmFoundInHim
# Command Line Interface

state = {'_exit_status': 0, "_var": {}}


def prompt(state):
    state_print(state)
    cmd = parse_input(input('> '))


def print_state(state):
    for key, val in state.items():
        if type(val) is str:
            if key[0] != '_':
               print(val, end=' ')
        elif type(val) is dict:
            try:
                print(val['__str__'], end=' ')
            except KeyError:
                pass
        elif type(val) in (list, tuple):
            if val != []:
                print(val[0], end=' ')


def parse_input(rawin):
    expressions = rawin.split('"')
    i = 0
    while i < len(expressions):
        # DOC: unseperated strings will be treated
        # as seperate expressions
        if expressions[i][-1] == '\\':
            expressions[i] += expressions.pop(i + 1)
            continue 
        if i % 2:
            expressions[i] = expressions[i].split('\'')<
        i += 1
    for i in len(expressions):
        
            
        
    
    

while not state['_exit_status']:
    state = prompt(state)
