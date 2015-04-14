#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "build_model.h"

#ifdef unix
#include <unistd.h>
#endif

#include <mikenet/simulator.h>

//INSERT_FLAG_INCLUDES

//INSERT_FLAG_CONSTANTS

int p,q;
Phase *phases[NUM_PHASES];
PhaseItem *phase_items[NUM_PHASE_ITEMS];
TestSet *test_sets[NUM_TEST_SETS];

void construct(Net *run_net) {
	/* create runNet which is a net struct containing all groups and connections.*/
	run_net=create_net(TIME);
	
	//INSERT_FLAG_BUILD_MAIN_NET
	
	/* done building the run_net object. all groups and connections are
	  accounted for. */
	
    /* define test sets: */
    
    //INSERT_FLAG_BUILD_TESTS

    /* define phase data: */
	  
    //INSERT_FLAG_BUILD_PHASES
    
    /* define individual phase item data: */
    
    //INSERT_FLAG_BUILD_PHASE_ITEMS
    
}