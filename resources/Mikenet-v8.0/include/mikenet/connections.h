/*
    mikenet - a simple, fast, portable neural network simulator.
    Copyright (C) 1995  Michael W. Harm

    This program is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

    See file COPYING for a copy of the GNU General Public License.

    For more info, contact: 

    Michael Harm                  
    HNB 126 
    University of Southern California
    Los Angeles, CA 90089-2520

    email:  mharm@gizmo.usc.edu

*/

#ifndef NET_H
#define NET_H

typedef struct tagGroup
{
  char *name;
  int numUnits;
  int index;         /* group specifier */
  char **unitNames;
  Real ** inputs;    /* indexed by time and unit */
  Real ** outputs;   /* indexed by time and unit */
  Real ** goalOutputs;   /* indexed by time and unit, used in crbp only */
  int activationType;  /* LOGISTIC_ACTIVATION or TANH_ACTIVATION */
  int bias;  /* is it a bias */
  Real biasValue;
  int numIncoming,numOutgoing;
  Real primeOffset;
  int scaling;  /* do we scale error (SCALE_NONE or SCALE_PROB) */
  Real *z,*backz; /* used by crbp */
  Real *taos;  /* time constants */
  Real **dedx;  /* indexed over time and units */
  Real **dydt;  /* indexed over time and units */
  Real *dedtao; 
  Real taoEpsilon; /* learning rate for time constants */
  Real temperature;
  Real targetNoise;  /* sd for gaussian noise added to target */
  Real clampNoise;  /* sd for gaussian noise added to input clamp */
  Real activationNoise; /* sd for gaussian noise on output */
  int resetActivation;  /* reset outputs to 0 at t=0? */
  Real errorRadius;
  int errorComputation;  /* SUM_SQUARED_ERROR or CROSS_ENTROPY */
  Real **goalInputs;  /* indexed by time, unit */
} Group;

typedef struct _tagConnections
{
  Real epsilon;
  Real momentum;
  Group * from, *to;  /* groups from and to */
  int ** frozen;   /* indexed by toUnit and fromUnit */
  Real ** weights;  /* ditto */
  Real ** backupWeights;  /* normally null, unless storeWeights called */
  Real weightNoise;
  Real ** gradients; /* ditto */  
  Real ** prevGradients;
  Real ** prevDeltas;
  Real ** v; /* used by almeida method */
  Real **h,**g;
  Real lambda;
  int useDBD;  /* do we use delta bar delta? */
  Real ** dbdWeight;
  Real dbdUp,dbdDown;  /* dbd up and down factor */
  int noisyUpdate;   /* boolean flag */
} Connections;  



typedef struct
{
  FILE *debugFile;
  int numConnections; /* how many connection sets do we have */
  Connections **connections;
  int numGroups;
  Group **groups;
  int pid; /* process id */
  int time;  /* how many ticks (max) */
  Real integrationConstant;
  int runfor;  /* how long to run for */
} Net;


Group *find_group_by_name(char *name);
Group * init_group(char *name,int numUnits,int time);



Group * init_bias(float val,int time); 
Connections * connect_groups(Group *g1, Group *g2);
Net * create_net();
Net * init_net();

void bind_connection_to_net(Net *net,Connections *c);
void unbind_connection_from_net(Net *net,Connections *c);
void bind_group_to_net(Net *net,Group *g);
void unbind_group_from_net(Net *net,Group *g);

int is_group_in_net(Group *g,Net *net);

int name_units(Group *g,char *fn);
void randomize_connections(Connections *c,Real weightRange);

extern Real default_weightDecay;
extern int default_noisyUpdate;
extern Real default_epsilon;
extern Real default_tao;
extern Real default_temperature;
extern int default_resetActivation;
extern int default_scaling;
extern Real default_errorRadius;
extern Real default_taoEpsilon;
extern Real default_weightNoise;
extern int default_activationType;
extern int default_errorComputation;
extern int globalNumGroups;  /* global number of groups defined */
extern Group **groups; /* global group list */
extern Real default_activationNoise;  
extern Real default_primeOffset;
extern int default_useDBD;
extern Real default_momentum;
extern Real default_dbdUp,default_dbdDown;

#endif
