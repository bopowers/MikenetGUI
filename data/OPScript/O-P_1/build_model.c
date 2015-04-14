#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "build_model.h"

#ifdef unix
#include <unistd.h>
#endif

#include <mikenet/simulator.h>

#include "/media/data/MikenetGUI/Reed/test_files/evaluator.c"

#define NUM_TEST_SETS 1
#define NUM_PHASES 1
#define NUM_PHASE_ITEMS 1
#define TIME 12
#define SEED 1
#define WEIGHT_RANGE 0.1
char run_name[]="O-P_1";

int p,q;
Phase *phases[NUM_PHASES];
PhaseItem *phase_items[NUM_PHASE_ITEMS];
TestSet *test_sets[NUM_TEST_SETS];

void construct(Net *run_net) {
	/* create runNet which is a net struct containing all groups and connections.*/
	run_net=create_net(TIME);
	
	Group *g1, *g2, *g3, *g4, *bias;
	Connections *c1, *c2, *c3, *c4, *c5, *c6, *c7, *c8, *c9;
	
	/* create all groups. 
	   format is: name, num of units,  ticks */ 
	g1=init_group("Ortho",10,TIME);
	g1->activationType=LOGISTIC_ACTIVATION;
	g1->errorComputation=SUM_SQUARED_ERROR;
	g2=init_group("OP_Hidden",10,TIME);
	g2->activationType=LOGISTIC_ACTIVATION;
	g2->errorComputation=SUM_SQUARED_ERROR;
	g3=init_group("Phono",10,TIME);
	g3->activationType=LOGISTIC_ACTIVATION;
	g3->errorComputation=SUM_SQUARED_ERROR;
	g4=init_group("Phono_Clean",10,TIME);
	g4->activationType=LOGISTIC_ACTIVATION;
	g4->errorComputation=SUM_SQUARED_ERROR;
	bias=init_bias(1.0,TIME);
	
	/* now add our groups to the run network object */ 
	bind_group_to_net(run_net,g1);
	bind_group_to_net(run_net,g2);
	bind_group_to_net(run_net,g3);
	bind_group_to_net(run_net,g4);
	bind_group_to_net(run_net,bias);
	
	/* now instantiate connection objects */ 
	c1=connect_groups(g1,g2);
	c2=connect_groups(g2,g3);
	c5=connect_groups(g4,g3);
	c4=connect_groups(g3,g4);
	c3=connect_groups(g3,g3);
	c6=connect_groups(bias,g1);
	c7=connect_groups(bias,g2);
	c8=connect_groups(bias,g3);
	c9=connect_groups(bias,g4);
	
	/* add connections to run network */ 
	bind_connection_to_net(run_net,c1);
	bind_connection_to_net(run_net,c2);
	bind_connection_to_net(run_net,c5);
	bind_connection_to_net(run_net,c4);
	bind_connection_to_net(run_net,c3);
	bind_connection_to_net(run_net,c6);
	bind_connection_to_net(run_net,c7);
	bind_connection_to_net(run_net,c8);
	bind_connection_to_net(run_net,c9);
	
	/* randomize the weights in the connection objects. 
	     2nd argument is weight range. */ 
	randomize_connections(c1,WEIGHT_RANGE);
	randomize_connections(c2,WEIGHT_RANGE);
	randomize_connections(c5,WEIGHT_RANGE);
	randomize_connections(c4,WEIGHT_RANGE);
	randomize_connections(c3,WEIGHT_RANGE);
	randomize_connections(c6,WEIGHT_RANGE);
	randomize_connections(c7,WEIGHT_RANGE);
	randomize_connections(c8,WEIGHT_RANGE);
	randomize_connections(c9,WEIGHT_RANGE);
		
	/* done building the run_net object. all groups and connections are
	  accounted for. */
	
    /* define test sets: */
    
test_sets[0]=(TestSet *)mh_calloc(sizeof(TestSet),1);
test_sets[0]->test_name=(char *)mh_malloc(12);
test_sets[0]->test_name="Treiman_Set";
test_sets[0]->test_examples=load_examples("/media/data/MikenetGUI/Reed/test_files/6k_treiman.ex",TIME);
test_sets[0]->args=(char **)mh_calloc(1,sizeof(char*));
test_sets[0]->args[0]=(char *)mh_calloc(13,sizeof(char));
test_sets[0]->args[0]="treiman_dict";


    /* define phase data: */
	  
	/* phase 1: */ 
	phases[0]=(Phase *)mh_calloc(sizeof(Phase),1);
	phases[0]->phase_name=(char *)mh_malloc(13);
	phases[0]->phase_name="defaultPhase";
	phases[0]->phase_order=0; //0=seq, 1=prob
	phases[0]->num_phase_items=1;
	phases[0]->max_iterations=1000;
	    
    /* define individual phase item data: */
    
	/* phase item 1: */ 
	Net *net1;
	net1=create_net(TIME);
	bind_group_to_net(net1,bias);
	bind_connection_to_net(net1,c1);
	bind_connection_to_net(net1,c2);
	bind_connection_to_net(net1,c3);
	bind_connection_to_net(net1,c4);
	bind_connection_to_net(net1,c5);
	phase_items[0]=(PhaseItem *)mh_calloc(sizeof(PhaseItem),1);
	phase_items[0]->net=net1;
	phase_items[0]->item_name=(char *)mh_malloc(12);
	phase_items[0]->item_name="OP_Training";
	phase_items[0]->which_phase=0;
	phase_items[0]->test_only=0;
	phase_items[0]->num_tests=1;
	phase_items[0]->test_indices=(int *)mh_calloc(1,sizeof(int));
	phase_items[0]->test_indices[0]=0;
	phase_items[0]->probability=0.0;
	phase_items[0]->total_group_readouts=0;
	phase_items[0]->total_activation_noise=0;
	phase_items[0]->total_input_noise=0;
	phase_items[0]->total_weight_noise=0;
	phase_items[0]->iter=0;
	phase_items[0]->wcount=0;
	phase_items[0]->ecount=0;
	phase_items[0]->tcount=0;
	phase_items[0]->ocount=0;
	phase_items[0]->error=0.0;
	
	phase_items[0]->train_examples=load_examples("/media/data/MikenetGUI/Reed/training_files/6ktraining.ex",TIME);
	phase_items[0]->epsilon=0.001;
	phase_items[0]->momentum=0.9;
	phase_items[0]->tolerance=0.1;
	phase_items[0]->error_radius=0.0;
	phase_items[0]->max_iterations=100000;
	phase_items[0]->training_mode=1;
	phase_items[0]->dbd=1;
	phase_items[0]->training_algorithm=0;
	phase_items[0]->reset_activation=1;
	phase_items[0]->stop_criterion=0;
	phase_items[0]->seconds=4.0;
	phase_items[0]->tai=0;
	phase_items[0]->error_ramp=1;
	phase_items[0]->tao=1.0;
	phase_items[0]->tao_max_mult=-1.0;
	phase_items[0]->tao_min_mult=0.001;
	phase_items[0]->tao_epsilon=0.0;
	phase_items[0]->tao_decay=0.0;
	phase_items[0]->will_save_weights=1;
	phase_items[0]->save_weights_interval=500;
	phase_items[0]->will_save_error=1;
	phase_items[0]->save_error_interval=1000;
	phase_items[0]->will_save_activations=1;
	phase_items[0]->save_activations_interval=500;
	phase_items[0]->test_interval=10000;
	
	    
}