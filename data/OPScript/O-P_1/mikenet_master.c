#include <stdio.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

#ifdef unix
#include <unistd.h>
#endif

#include "build_model.h"
#include "build_model.c"
#include <mikenet/simulator.h>

int phase_table[NUM_PHASES][NUM_PHASES];
int run_iter_counter=0;
Real error;
Net *run_net;

void makePhaseTable(PhaseItem *phArray[]) {
	int i,j;
	int seq_count;
	//create a 2D array where rows are phases, and cols are phase items
	//in all positions, a nonzero value indicates phase item j is in phase i.
	for(i=0;i<NUM_PHASES;i++) {
		seq_count=0;
		for(j=0;j<NUM_PHASE_ITEMS;j++) {
			if(phArray[j]->which_phase == i) {
				seq_count++;
				phase_table[i][j] = seq_count;
				//note that phase items were written in order, and a phase item exists in
				//on and only one phase. since seq_count monotonically increases, we can
				//let it define sequential order for items within a phase.
				//for probabilistic interleaved blocks, all that matters is the value
				// is nonzero!
			} else {
				phase_table[i][j] = 0;
			}
		}
	}
}

int probabilisticChooseItem(float propArray[]) {
	//prepare insertion sort of both the probabilities AND their corresponding
	//phase indices...
	int i,ans;
	Real sortArray[2][NUM_PHASE_ITEMS]; //first row: probabilities, second: indices
	for(i=0;i<NUM_PHASE_ITEMS;i++) {
		sortArray[0][i] = propArray[i];
		sortArray[1][i] = (Real) i;
	}
	//insertion sort
	Real valueToInsert_0, valueToInsert_1;
	int holePos;
	for (i=1;i<NUM_PHASE_ITEMS;i++) {
		valueToInsert_0 = sortArray[0][ i ];
		valueToInsert_1 = sortArray[1][ i ];
		holePos = i;
		
		while (holePos > 0 && valueToInsert_0 < sortArray[0][holePos - 1]) {
			sortArray[0][holePos] = sortArray[0][holePos - 1];
			sortArray[1][holePos] = sortArray[1][holePos - 1];
			holePos--;
		}
		sortArray[0][holePos] = valueToInsert_0;
		sortArray[1][holePos] = valueToInsert_1;
	}
	
	//sortArray now contains sorted probabilities (row 0) 
	//and corresponding phase array indices (row 1)...
	//to convert this to a CDF, need to make each row 0 value equal
	//the sum of itself and all previous values...
	for (i=1;i<NUM_PHASE_ITEMS;i++) {
		sortArray[0][ i ] += sortArray[0][ i - 1 ];
	}
	//finally compare random number, u, on [0,1] to each row 0 value and return the
	//phase index (row 1) at the first spot for which row 0 is larger than u
	Real u;
	u = mikenet_random();
	ans=0;
	for (i=0;i<NUM_PHASE_ITEMS;i++) {
		if(u < sortArray[0][i]) {
			ans = (int)sortArray[1][i];
			break;
		}
	}
	return ans;
}

void setPhaseItemParameters(PhaseItem *ph) {
	ph->net->tai=ph->tai;
	ph->net->integrationConstant=(float)ph->seconds/(float)TIME;
	int c,g,u,ng,nc;
	for (g=0;g<ph->net->numGroups;g++) {
		ph->net->groups[g]->errorRamp=ph->error_ramp;
		ph->net->groups[g]->resetActivation=ph->reset_activation;
		ph->net->groups[g]->errorRadius=ph->error_radius;
		ph->net->groups[g]->taoMaxMultiplier=ph->tao_max_mult;
		ph->net->groups[g]->taoMinMultiplier=ph->tao_min_mult;
		ph->net->groups[g]->taoEpsilon=ph->tao_epsilon;
		ph->net->groups[g]->taoDecay=ph->tao_decay;
		for (u=0;u<ph->net->groups[g]->numUnits;u++) {
			ph->net->groups[g]->taos[u]=ph->tao;
		}
        //NOISE...only look for specified noise values to add.
        //otherwise, the default value of 0.0 will be used automatically.
        
        //activation noise
        if (ph->total_activation_noise > 0) {
            for (ng=0;ng<ph->total_activation_noise;ng++) {
                if (strcmp(ph->net->groups[g]->name, ph->activation_noise_groups[ng]->name) == 0) {
                    //apply activation noise to this group
                    ph->net->groups[g]->activationNoise = ph->activation_noise_values[ng];
                    break;
                }
            }
        }
        //input noise
        if (ph->total_input_noise > 0) {
            for (ng=0;ng<ph->total_input_noise;ng++) {
                if (strcmp(ph->net->groups[g]->name, ph->input_noise_groups[ng]->name) == 0) {
                    //apply input noise to this group
                    ph->net->groups[g]->inputNoise = ph->input_noise_values[ng];
                    break;
                }
            }
        }

	}
	for (c=0;c<ph->net->numConnections;c++) {
		ph->net->connections[c]->epsilon=ph->epsilon;
		ph->net->connections[c]->momentum=ph->momentum;

        //NOISE...only look for specified noise values to add.
        //otherwise, the default value of 0.0 will be used automatically.
        
        //weight noise type and value assigned together
        if (ph->total_weight_noise > 0) {
            for (nc=0;nc<ph->total_weight_noise;nc++) {
                if (strcmp(ph->net->connections[c]->from->name,
                           ph->weight_noise_connections[nc]->from->name) == 0 &&
                    strcmp(ph->net->connections[c]->to->name,
                           ph->weight_noise_connections[nc]->to->name) == 0) {
                    //use the specified weight noise type
                    if (ph->weight_noise_types[nc] > 0) {
                        ph->net->connections[c]->weightNoiseType = ph->weight_noise_types[nc];
                        //assign the weight noise value
                        ph->net->connections[c]->weightNoise = ph->weight_noise_values[nc];
                        break;
                    }
                }
            }
        }
	}
}

void printReadouts(PhaseItem *ph, ExampleSet *trainOrTest) {
	/*This method is unfortunately nonlinear, but only as a function of a hopefully small
	   number of groups/ticks.*/
	if (ph->total_group_readouts == 0) {
		//not printing activations
	} else {
		printf("saving unit activation values...\n");
		char fileNames[128];
		sprintf(fileNames,"%s_%d.activations",run_name,run_iter_counter);
		FILE *fp;
		fp=fopen(fileNames, "w");
		int currGroup,currUnit,currTime,ts,j,tSlices;
		Example *currEx;
		for(j=0;j<trainOrTest->numExamples;j++) {
			currEx=&trainOrTest->examples[j];
			fprintf(fp,"\n");
			fprintf(fp,"example:\t%s\n",currEx->name);
			fprintf(fp,"event\tgroup\tunit\t");
			//total number of readout slices = tSlices
			tSlices=sizeof(ph->group_readout_times)/sizeof(ph->group_readout_times[0]); 
			for (ts=0;ts<tSlices;ts++) {
				fprintf(fp,"t%d\t",ph->group_readout_times[ts]);
			}
			fprintf(fp,"\n%s",ph->item_name);
			bptt_forward(ph->net,currEx);
			for (currGroup=0;currGroup<ph->total_group_readouts;currGroup++) {
				Group *thisGroup = find_group_by_name(ph->group_readout_names[currGroup]);

				
				
				for (currUnit=0;currUnit<thisGroup->numUnits;currUnit++) {
					fprintf(fp,"%s\t%d\t",thisGroup->name,currUnit);
					for (currTime=0;currTime<tSlices;currTime++) {

						if (ph->readout_table[currGroup][ph->group_readout_times[currTime]] == 1) {
							fprintf(fp,"%f\t",thisGroup->outputs[ph->group_readout_times[currTime]][currUnit]);
						} else {
							fprintf(fp,"\t");
						}
					}
					fprintf(fp,"\n");
				}
				
				fprintf(fp,"\n");
				
			}
			
			
		}
		fclose(fp);
	}	
}

void test(PhaseItem *ph) {
	//do all the tests assigned to this phase item, if any
	int i,t;
	if(ph->num_tests == 0)
		return;
	printf("testing network...\n");
	for(i=0;i<ph->num_tests;i++) {
		t = ph->test_indices[i];
		char fileNames[128];
		sprintf(fileNames,"%s_%d.test",test_sets[t]->test_name,run_iter_counter);
		//test set can also provides arguments that will be passed to a function called
		//"myTestFunction(args)". that function needs to be defined in its own C script
		//which can include any other supplementary files. any additional arguments
		//are required to be strings. see Help for more info!
		
		//required format: myTestFunction(char *filename, Net *n, ExampleSet *x, char **optionalargs)
		#ifdef USE_TESTING
		myTestFunction(fileNames, ph->net, test_sets[t]->test_examples, test_sets[t]->args);
		#endif
	}
}

void onlineTrainProcedure(PhaseItem *ph) {
	Example *ex;
	/* get random example from exampleset */
	ex=get_random_example(ph->train_examples);
	/* do forward propagation */
	if (ph->training_algorithm == 0) {
		/* bptt */
		bptt_forward(ph->net,ex);
		/* backward pass: compute gradients */
		bptt_compute_gradients(ph->net,ex);
	} else {
		/* crbp */
		crbp_forward(ph->net,ex);
		/* backward pass: compute gradients */
		crbp_compute_gradients(ph->net,ex);
	}
	/* sum up error for this example */
	ph->error+=compute_error(ph->net,ex);
	/* online learning: apply the deltas
	from previous calls to compute_gradients */
	if (ph->training_algorithm == 0) {
		/* bptt */
		bptt_apply_deltas(ph->net);
	} else {
		/* crbp */
		crbp_update_taos(ph->net);
		crbp_apply_deltas(ph->net);
	}
}

void batchTrainProcedure(PhaseItem *ph) {
	int j;
	Example *ex;
	ExampleSet *exSet=ph->train_examples;
	for(j=0;j<exSet->numExamples;j++) {
		/* get j'th example from exampleset */
		ex=&exSet->examples[j];
		if (ph->training_algorithm == 0) {
			/* bptt */
			bptt_forward(ph->net,ex);
			/* backward pass: compute gradients */
			bptt_compute_gradients(ph->net,ex);
		} else {
			/* crbp */
			crbp_forward(ph->net,ex);
			/* backward pass: compute gradients */
			crbp_compute_gradients(ph->net,ex);
		}

		/* sum up error for this example */
		ph->error+=compute_error(ph->net,ex);
	}

	/* batch learning: apply the deltas accumulated
	from previous calls to compute_gradients1 */
	if (ph->training_algorithm == 0) {
		/* bptt */
		if (ph->dbd)
			bptt_apply_deltas_dbd_momentum(ph->net);
		else
			bptt_apply_deltas_momentum(ph->net);
	} else {
		/* crbp */
		crbp_update_taos(ph->net);
		crbp_apply_deltas(ph->net);
	}
}

void train(PhaseItem *ph, int interleaving) {
	//, FILE *error_file) {
	//variables
	int i,j;
	
	Net *net=ph->net;
	setPhaseItemParameters(ph);
	
	while(1) {
		run_iter_counter++; //a global counter for the whole run (across all individual phase items)
		ph->iter++;
		ph->ecount++;
		ph->wcount++;
		ph->ocount++;
		ph->tcount++;
		i=ph->iter; //need this for interleaving so you don't keep reinitializing to 0
		
		if (i > ph->max_iterations && ph->stop_criterion < 2 && interleaving == 0) {
			run_iter_counter--;
			//did we already save the final weights?
			if (ph->max_iterations % ph->save_weights_interval != 0) {
				char fileNames[128];
				sprintf(fileNames,"%s_%d.weights",run_name,run_iter_counter);
				save_state(net,fileNames);
			}
			//did we already save the final error?
			if (ph->max_iterations % ph->save_error_interval != 0) {
				/* save average error to error file*/
				printf("avgError:\t%s\t%d\t%d\t%f\n",ph->item_name,run_iter_counter,i-1,ph->error);
			}
			printf("end of training...maximum iterations reached\n");
            /* pop out of loop */
			break;
		}
		
		/* don't apply momentum until after 10th iteration
		 (see Plaut et al. 1996) */
		if (i>10) {
			for(j=0;j<net->numConnections;j++)
				net->connections[j]->momentum=ph->momentum;
		} else {
			for(j=0;j<net->numConnections;j++)
				net->connections[j]->momentum=0.0;
		}
		/* training happens here according to the training mode */
		if (ph->training_mode == 0) {
			/* batch */
			batchTrainProcedure(ph);
		} else {
			/* online */
			onlineTrainProcedure(ph);
		}
		
		/* is it time to write error? */
		if (ph->ecount==ph->save_error_interval) {
			/* average error over last 'ecount' iterations */
			ph->error = ph->error/(float)ph->ecount;
			ph->ecount=0;
			/* save average error to error file*/
			printf("avgError:\t%s\t%d\t%d\t%f\n",ph->item_name,run_iter_counter,i,ph->error);
			
			/* has error dipped below tolerance? */
			if (ph->error < ph->tolerance && ph->stop_criterion >= 1 && interleaving == 0) {
				//save weights at this moment
				char fileNames[128];
				sprintf(fileNames,"%s_%d.weights",run_name,run_iter_counter);
				save_state(net,fileNames);
				/* pop out of loop */
				printf("end of training...error threshold reached\n");
				break;
			}
			/* zero error; start counting again */
			ph->error = 0.0;
		}
		/* is it time to save weights? */
		if (ph->wcount==ph->save_weights_interval)	{
			if (ph->will_save_weights == 1) {
				char fileNames[128];
				sprintf(fileNames,"%s_%d.weights",run_name,run_iter_counter);
				save_state(net,fileNames);
				ph->wcount=0;
			}
		}
		/* is it time to save activations? */
		if (ph->will_save_activations==1 && 
		     ph->ocount==ph->save_activations_interval)	{
			printReadouts(ph,ph->train_examples);
			ph->ocount=0;
		}
		/* is it time to test? */
		if (ph->tcount==ph->test_interval && ph->tcount != 0)	{
			test(ph);
			ph->tcount=0;
		}
		
		if(interleaving == 1) {
			//we only run once.
			//this code is wrapped, and early stopping is handled outside...
			break;
		}
	}
}

void doInterleavingPhase(int this_phase, Phase **phArray, PhaseItem **itemArray) {
	//, FILE *error_file) {
	PhaseItem *ph;
	int i,pi;
	Real proportions[NUM_PHASE_ITEMS];
	//only consider probabilities for phases in the current block
	for(i=0;i<NUM_PHASE_ITEMS;i++) {
		if(phase_table[this_phase][i] > 0) {
			proportions[i] = itemArray[i]->probability;
		} else {
			proportions[i] = 0.0;
		}
	}
	//begin interleaving procedure
	i=0;
    while(i < phArray[this_phase]->max_iterations) {
		i++;
	    //first, probabilistically choose phase item.
		pi = probabilisticChooseItem(proportions);
		ph = phase_items[pi];
		if (ph->training_mode == 0) {
			printf("training %s in batch mode...\n",ph->item_name);
		} else {
			printf("training %s in online mode...\n",ph->item_name);
		}
		train(ph,1);
		//train(ph,1,error_file);
	}
	//save weights at this moment
	char fileNames[128];
	sprintf(fileNames,"%s_%d.weights",run_name,run_iter_counter);
	printf("end of interleaving phase...maximum iterations reached\n");
}

int main(int argc,char *argv[]) {
	int ph,nz;
	mikenet_set_seed(SEED);
	setbuf(stdout,NULL);
	//announce_version();
	
	//build the model -- creates structs for each phase, and also for each phase item.
	//defined in build_model.c. Note: "phases" and "phase_items" are visible from here.
	construct(run_net);
	
	//now lay out the phase item table: the purpose of this table is to handle multiple
	//phase items within each phase. phase items can be presented in just simple sequential 
	//order (default), or they could be nondeterministically interleaved.
	//the data structure to organize this is an int[][] array, which is created by calling
	//makePhaseTable(). phases are rows, and individual phase items correspond to columns.
	makePhaseTable(phase_items);
	
	/* open an error file to output error
	FILE *error_file;
	char e_filename[128];
	sprintf(e_filename,"%s.error",run_name);
	error_file = fopen(e_filename,"a");
	*/
	
	//start at the first phase, row 0 of phase_table
	for(ph=0;ph<NUM_PHASES;ph++) {
        int i;
        //print noise data to the log file. this includes noise type, which group/connection
        //to apply the noise to, and the noise amount.
        //note this might change for each phase item, so we do it here

        for(i=0;i<NUM_PHASE_ITEMS;i++) {
            if(phase_table[ph][i] ==0) {
                //skip
            } else {
                for (nz=0;nz<phase_items[i]->total_activation_noise;nz++) {
                    printf("noiseData:\t%s\tactivation\t%s\t%f\n",phase_items[i]->item_name,
                           phase_items[i]->activation_noise_groups[nz]->name,phase_items[i]->activation_noise_values[nz]);
                }
                
                for (nz=0;nz<phase_items[i]->total_input_noise;nz++) {
                    printf("noiseData:\t%s\tinput\t%s\t%f\n",phase_items[i]->item_name,
                           phase_items[i]->input_noise_groups[nz]->name,phase_items[i]->input_noise_values[nz]);
                }
                
                for (nz=0;nz<phase_items[i]->total_weight_noise;nz++) {
                    if (phase_items[i]->weight_noise_types[nz] == 1) {
                        printf("noiseData:\t%s\tweight_additive\t%s->%s\t%f\n",phase_items[i]->item_name,
                               phase_items[i]->weight_noise_connections[nz]->from->name,
                               phase_items[i]->weight_noise_connections[nz]->to->name,
                               phase_items[i]->weight_noise_values[nz]);
                    } else {
                        printf("noiseData:\t%s\tweight_multiplicative\t%s->%s\t%f\n",phase_items[i]->item_name,
                               phase_items[i]->weight_noise_connections[nz]->from->name,
                               phase_items[i]->weight_noise_connections[nz]->to->name,
                               phase_items[i]->weight_noise_values[nz]);
                    }
                }
            }
		}

		if(phases[ph]->phase_order == 0) {
			//sequential block, default
			printf("starting phase %s\nusing sequential order...\n",phases[ph]->phase_name);

			for(i=0;i<NUM_PHASE_ITEMS;i++) {
				if(phase_table[ph][i] ==0) {
					//skip
				} else {
					//for this phase determine if it is train (batch or online) or test
					if(phase_items[i]->test_only == 0) {
						if(phase_items[i]->training_mode == 0) {
							printf("training %s in batch mode...\n",phase_items[i]->item_name);
						} else {
							printf("training %s in online mode...\n",phase_items[i]->item_name);
						}
						train(phase_items[i],0);
						//train(phase_items[i],0,error_file);
					} else {
						//testing only
						test(phase_items[i]);
					}
				}
			}
			
		} else {
			//this block will use probabilistic interleaving
			printf("starting phase %s\nusing probabilistic interleaving...\n",
			        phases[ph]->phase_name);
			doInterleavingPhase(ph,phases,phase_items);
			//doInterleavingPhase(ph,phases,phase_items,error_file);
		}
	}
	printf("simulation complete. exiting now.\n");
	FILE *f;
    f = fopen("db_flag","w");
    fclose(f);
	/*fclose(error_file)*/
  return 0;
}
