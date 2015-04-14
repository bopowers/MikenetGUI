#ifndef USERDEF_H
#define USERDEF_H

#include <mikenet/simulator.h>

typedef struct {
	ExampleSet *test_examples;
    char *test_name;
    char **args;
} TestSet;

typedef struct {
	Net *net;
    
    /* some simple counters */
    int iter; // trial
    int wcount; // weight save
    int ecount; // error save
    int tcount; // test
    int ocount; // activations save
    
    char *item_name; // an identifier
	int which_phase; // which Phase do I belong to?
	int test_only; // by default, PhaseItem is a training set
    int num_tests;
	int *test_indices; // indices of global testSet array
	Real probability; // if probabilistic training, what proportion of trials?
	
	/* activation saving parameters */
	int total_group_readouts; // how many groups are you getting activations from?
	char **group_readout_names; // which groups?
	int *group_readout_times; // which times?
	int **readout_table; // table with time slices for each group
	
	/* noise */
    int total_weight_noise;
    int total_activation_noise;
    int total_input_noise;
    
    int *weight_noise_types;
    Real *weight_noise_values;
    Real *activation_noise_values;
    Real *input_noise_values;
    
    Connections **weight_noise_connections;
    Group **activation_noise_groups;
    Group **input_noise_groups;

	/* the remaining variables are specifically for training */
	ExampleSet *train_examples;
	int max_iterations;
	int stop_criterion;
	Real error;
	Real epsilon;
	Real tolerance;
	Real momentum;
	Real error_radius;
	int training_mode; // batch=0, online=1
	int training_algorithm; // bptt=0, crbp=1
	
	/* printing and saving */
	int will_save_weights;
	int save_weights_interval;
	int will_save_error;
	int save_error_interval;
	int test_interval;
	int will_save_activations;
	int save_activations_interval;
	int readout_interval;
	
	/* additional parameters */
	int error_ramp;
	int tai;
	int dbd;
	int reset_activation;
    Real seconds;
	Real tao;
	Real tao_decay;
	Real tao_max_mult;
	Real tao_min_mult;
	Real tao_epsilon;
	
} PhaseItem;

typedef struct {
	char *phase_name;
	int phase_order;
	int num_phase_items;
	int max_iterations;
} Phase;

void construct();

#endif