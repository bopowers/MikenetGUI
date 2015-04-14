#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include <mikenet/simulator.h>

#include "simconfig.h"

/* These two lines are for the benefit of the master.c code
   They must be included for it to work.................................*/
#define USE_TESTING 0
void myTestFunction(char *fname, Net *n, ExampleSet *x, char **args);
/*......................................................................*/

int debug=0;

ExampleSet *examples;

typedef struct
{
  char ch;
  Real vector[PHO_FEATURES];
} Phoneme;

Phoneme phonemes[50];
int phocount=0;

int symbol_hash[255];

int NUM_WORDS=0;

char words[10000][15];
char words_pho[10000][15];
char words_pho2[10000][15];

int illegal_test(char *euc,char *thresh)
{
  int i;
  for(i=0;i<PHO_SLOTS;i++)
    {
      if (thresh[i]=='?' && euc[i]!='_')
	return 1;
    }
  return 0;
}


void noise_connection(Connections *c,float n)
{
  int i,j;

  for(i=0;i<c->to->numUnits;i++)
    for(j=0;j<c->from->numUnits;j++)
      {
	c->weights[i][j] *= 1.0 + 
	  n * gaussian_number();
      }
}

int isbad(char *output,char *target,char *converted,int *didconvert)
{
  int i;
  char v1[15],v2[15];

  *didconvert=0;
  strcpy(converted,target);

  if (debug)
    printf("entering is_bad\n");

  if (target==NULL) return 1;
  if (target[0]==0) return 1;

  if (debug)
    printf("main strcmp test\n");


  if (strcmp(output,target)==0)
    return 0;

  if (debug)
    printf("consonant test\n");


  if (output[0]!=target[0])
    return 1;

  if (output[1]!=target[1])
    return 1;

  if (output[4]!=target[4])
    return 1;

  if (output[5]!=target[5])
    return 1;

  if (debug)
    printf("passed initial tests\n");
  
  strncpy(v1,&output[2],2);
  strncpy(v2,&target[2],2);
  v1[2]=0;
  v2[2]=0;
  
  if (strcmp(v1,"e_")==0 && strcmp(v2,"ej")==0)
    {
      converted[3]='_';
      *didconvert=1;
      return 0;
    }

  if (strcmp(v1,"o_")==0 && strcmp(v2,"ow")==0)
    {
      converted[3]='_';
      *didconvert=1;
      return 0;
    }

  if (strcmp(v1,"ow")==0 && strcmp(v2,"o_")==0)
    {
      converted[3]='w';
      *didconvert=1;
      return 0;
    }

  if (strcmp(v1,"o_")==0 && strcmp(v2,"ow")==0)
    {
      converted[3]='_';
      *didconvert=1;
      return 0;
    }

  if (strcmp(v1,"a_")==0 && strcmp(v2,"c_")==0)
    {
      converted[2]='a';
      *didconvert=1;
      return 0;
    }

  if (strcmp(v1,"c_")==0 && strcmp(v2,"a_")==0)
    {
      converted[2]='c';
      *didconvert=1;
      return 0;
    }

  if (debug)
    printf("returning 1; v1 %s v2 %s\n",v1,v2);

  return 1;
}

void load_items(char *key)
{
  FILE *f;
  int i;
  char line[255];
  char *p;

  f=fopen(key,"r");
  if (f==NULL)
    Error0("can't open key file\n");

  fgets(line,255,f);
  i=0;
  while(!feof(f))
    {
      p=strtok(line," \t\n");
      strcpy(words[i],p);
      p=strtok(NULL," \t\n");
      p=strtok(NULL," \t\n");
      strcpy(words_pho[i],p);
      words_pho[i][PHO_SLOTS]=0;
      p=strtok(NULL," \t\n");
      if (p && ((p[0]>='a' && p[0]<='z') || p[0]=='_'))
	strcpy(words_pho2[i],p);
      else
	strcpy(words_pho2[i],"");
      words_pho2[i][PHO_SLOTS]=0;
      i++;
      fgets(line,255,f);
    }
  fclose(f);
  NUM_WORDS=i;
}

float nonword_error(Real *vec,char *t1,char *t2) {
	float e1=0,e2=0,e,d1,d2;
	char c;
  	int v,i,j;
  	for(i=0;i<PHO_SLOTS;i++) {
    	v=symbol_hash[(unsigned int)t1[i]];
      	if (v == -1) {
	  		fprintf(stderr,"error on hash lookup, char %c\n",t2[i]);
	  		exit(0);
		}
      	d1=0;
      	d2=0;
      	for(j=0;j<PHO_FEATURES;j++) {
	  		e=vec[i*PHO_FEATURES+j] - phonemes[v].vector[j];
	  		d1 += e * e;
		}
		
      	if ((t2[0]!=0) && (t2[i] != t1[i])) {
	  		v=symbol_hash[(unsigned int)t2[i]];
	  		if (v == -1) {
	      		fprintf(stderr,"error on hash lookup, char %c\n",
		      	t2[i]);
	      		exit(0);
	    	}
	  		for(j=0;j<PHO_FEATURES;j++) {
	      		e=vec[i*PHO_FEATURES+j] - phonemes[v].vector[j];
	      		d2 += e * e;
	    	}
		} else {
			d2=d1;
		}
    	e1 += d1;
    	e2 += d2;
	}
	if (e1 < e2)
    	return e1;
  	else return e2;
}

void load_phonemes() {
	FILE * f;
	char line[255],*p;
	int i,x;
	f=fopen("../../../test_files/mapping","r");
	if (f==NULL) {
		fprintf(stderr,"no mapping file\n");
      	exit(1);
	}
  	x=0;
  	fgets(line,255,f);
	while(!feof(f)) {
    	p=strtok(line," \t\n");
    	if (p[0]=='-') {
			p[0]='_';
		}
    	phonemes[phocount].ch=p[0];
    	symbol_hash[(unsigned int)(p[0])]=x++;
    	for(i=0;i<PHO_FEATURES;i++) {
	  		p=strtok(NULL," \t\n");
	  		if (strcmp(p,"NaN")==0) {
	    		phonemes[phocount].vector[i]= -10;
	  		} else { 
	    		phonemes[phocount].vector[i]= atof(p);
	  		}
		}
      	phocount++;
      	fgets(line,255,f);
    }
  fclose(f);
}


float euclid_distance(Real *x1,Real *x2)
{
  float d=0,r;
  int i;
  for(i=0;i<PHO_FEATURES;i++)
    {
      r = x1[i] - x2[i];
      d += r * r;
    }
  return d;
}
      
Real euclid(Real *v,char *out)
{
  int i,j;
  int nearest_item;
  float error=0;
  float nearest_distance,d;

  for(i=0;i<PHO_SLOTS;i++)
    {
      nearest_item=-1;
      for(j=0;j<phocount;j++)
	{
	  d=euclid_distance(&v[i*PHO_FEATURES],phonemes[j].vector);
	  if ((nearest_item == -1) ||
	      (d < nearest_distance))
	    {
	      nearest_item=j;
	      nearest_distance=d;
	    }
	}
      error += d;
      out[i]=phonemes[nearest_item].ch;
    }
  out[PHO_SLOTS]=0;
  return nearest_distance;
}


int thresh(Real *v,char *out,float threshold)
{
  int i,j,wrong,ok,k;
  float error=0,e;
  int illegal=0;

  for(i=0;i<PHO_SLOTS;i++)
    {
      ok = -1;
      for(j=0;j<phocount;j++)
	{
	  wrong=0;
	  for(k=0;k<PHO_FEATURES;k++)
	    {
	      e=fabs(v[i*PHO_FEATURES+k] - phonemes[j].vector[k]);
	      if (e > threshold)
		{
		  wrong=1;
		  break;
		}
	    }
	  if (wrong==0)
	    {
	      ok=j;
	      break;
	    }
	}
      if (ok == -1)
	{
	  out[i]='?';
	  illegal=1;
	}
      else out[i]=phonemes[ok].ch;
    }
  out[PHO_SLOTS]=0;
  return illegal;
}


void get_name(char *tag, char *name)
{
  char *p;
  p=strstr(tag,"Word:");
  p+= 5;
  p=strtok(p," \t\n");
  strcpy(name,p);
}

void myTestFunction(char *filename, Net *net, ExampleSet *examples, char **myargs) {
	int didconvert;
  	char converted[10];
  	int test_illegal=0;
  	int ill;
  	Real dx;
  	StatStruct *stats;
  	char fn[255];
  	int illegal=0;
  	int verbose=0;
  	char euclid_output[15],euclid_target[15],name[40];
  	char thresh_output[15],thresh_target[15];
  	Real dice,range;
  	Example *ex;
  	int i,count,j,save;
  	Real error;
  	Real dx_cutoff=100000000.0;
  	float threshold=0.25;
  	int thresh_wrong;
  	int euclid_wrong,euclid_wrongs;
  	int thresh_wrongs;
  	int new_wrongs=0,new_wrong;
  	char *keyFile=NULL;
    
  	/* unpack the args */
  	int kFileLength = strlen(myargs[0]);
  	keyFile = (char *)mh_malloc(kFileLength+1);
  	keyFile = myargs[0];

  	/* we're writing the output to a file specified by filename */
  	FILE *fp;
  	fp=fopen(filename, "w");
    
  	/* initialize what we need */
  
  	Group *output=find_group_by_name("Phono");
    
  	stats=get_stat_struct();

  	for(i=0;i<255;i++) {
    	symbol_hash[i]=-1;
    }
  
  	load_phonemes();
  	load_items(keyFile);
  
  	/* NOT restricting number of words, since this will vary between test sets
  	if (examples->numExamples != NUM_WORDS)
    	Error2("not enough words in examplefile; file has %d and needs %d",
	   	examples->numExamples,NUM_WORDS);
   	*/

  	error=0.0;
  	count=0;
  	save=1;
  	euclid_wrongs=0;
  	new_wrongs=0;
  	thresh_wrongs=0;

  	clear_stats(stats);
  	strcpy(thresh_target,"");
  	strcpy(euclid_target,"");
  	illegal=0;

  	euclid_wrongs=0;
  	thresh_wrongs=0;
  	illegal=0;
  	clear_stats(stats);

  	/* loop for ITER number of times */
  	for(i=0;i<examples->numExamples;i++) {
    	ex=&examples->examples[i];
      	crbp_forward(net,ex);
      	push_item(error,stats);
      	euclid(output->outputs[SAMPLES-2],euclid_output);
      	euclid_wrong=0;
      	get_name(ex->name,name);
      	fprintf(fp,"%s\t",name);
      	if (isbad(euclid_output,words_pho[i],converted,&didconvert)==0) {
	  		if (didconvert) {
	    		error=nonword_error(output->outputs[SAMPLES-2],converted,"");
	  		} else {
	    		error=nonword_error(output->outputs[SAMPLES-2],
					words_pho[i],words_pho2[i]);
		  	}
		} else if (isbad(euclid_output,words_pho2[i],converted,&didconvert)==0) {
	  		if (didconvert) {
	    		error=nonword_error(output->outputs[SAMPLES-2],converted,"");
	  		} else {
	    		error=nonword_error(output->outputs[SAMPLES-2],
					words_pho[i],words_pho2[i]);
			}
		} else {
	  		error=nonword_error(output->outputs[SAMPLES-2],
			      words_pho[i],words_pho2[i]);
	  		euclid_wrong=1;
	  		euclid_wrongs++;
		}
      	error=nonword_error(output->outputs[SAMPLES-2],
			words_pho[i],words_pho2[i]);
		
      	thresh_wrong=0;
      	new_wrong=0;

		#ifdef FOO      

      	ill=thresh(output->outputs[SAMPLES-2],thresh_output,threshold);
      	illegal+=ill;

      	if ((isbad(thresh_output,words_pho[i])!=0) &&
	  		(isbad(thresh_output,words_pho2[i])!=0)) {
	  		thresh_wrongs++;
	  		thresh_wrong=1;
		} else thresh_wrong=0;

      	if (test_illegal)
			ill=illegal_test(euclid_output,thresh_output);
      	else ill=0;

      	if (euclid_wrong > 0 || ill > 0) {
	  		new_wrongs++;
	  		new_wrong=1;
		} else new_wrong=0;
		#endif

      	fprintf(fp,"%.2f\t/%s/\t%s\t%s\t",error,
	    	euclid_output,words_pho[i],words_pho2[i]);
	     
      	if (euclid_wrong) {
			fprintf(fp,"[euclid_wrong]\t");
		}
	
      	if (thresh_wrong) {
			fprintf(fp,"[thresh_wrong]\t");
		}
      	if (new_wrong) {
      		fprintf(fp,"[new_wrong]");
      	}
      	fprintf(fp,"\n");
      	if (verbose) {
	  		for(j=0;j<output->numUnits;j++)
	    		fprintf(fp,"%4.1f\t%4.1f\n",
		   			output->outputs[SAMPLES-2][j],
		   			ex->targets[output->index][SAMPLES-2][j]);
		}
    }

  fclose(fp);
  // database won't have field names for these data, so save field names and data types to a file
  fp=fopen("test_headers", "w");
  fprintf(fp,"word TEXT\nsse REAL\nresponse TEXT\ntarget1 TEXT\ntarget2 TEXT\naccuracy TEXT");
  fclose(fp);
}

