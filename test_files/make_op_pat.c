#include <stdio.h>
#include <math.h>
#include <string.h>
#include <stdlib.h>
#include "simconfig.h"


char vector[256][PHO_FEATURES][6];

char ortho_vowels[]="aeiouwy";
#define MAX_ORTH 14

int ortho_features[MAX_ORTH+1][26];

void get_map(char pho,int index,char *txt,char *word)
{
  char *s;
  s=vector[(unsigned char)pho][index];
  if ((pho==' ') || (pho=='\t') || (pho==0))
    {
      strcpy(txt,"0 ");
      return;
    }
  else if (s[0]==0)
    {
      fprintf(stderr,"can't find lookup for phoneme \"%c\"\"%d\" word %s\n",pho,pho,word);
      return;      
    }
  strcpy(txt,s);
}


void print_it(char *word,char *orth,char *phoneme,float prob,int *sem)
{
  int i,j,x;
  char txt[500];
  int out[1000];

  if (orth[MAX_ORTH-1] != '_')
    {
      fprintf(stderr,"rejecting %s\n",word);
      return;
   }
  printf("TAG Word: %s Pho: %s Ortho: %s\n",word,phoneme,orth);
  printf("PROB %f\n",prob);

  for(i=0;i<ORTHO_FEATURES;i++)
    out[i]=0;

  for(i=0;i<MAX_ORTH;i++)
    {
      if (orth[i]!='_')
	{
	  out[ortho_features[i][orth[i]-'a']] =1;
	}
    }

  printf("CLAMP Ortho ALL FULL\n");

  for(i=0;i<ORTHO_FEATURES;i++)
    printf("%d ",out[i]);

  /* now do targets */


  printf("\n");

    printf("TARGET Phono %d-%d FULL\n",SAMPLES-2,SAMPLES-1);
    for(i=0;i<strlen(phoneme);i++)
    {         
      for(j=0;j<PHO_FEATURES;j++)
	{
	  get_map(phoneme[i],j,txt,word);
	  printf("%s ",txt);
	}
      printf("\n");
    }
  printf(";\n");
}
void load_mapping()
{
  FILE *f;
  char line[4000];
  char *ch,*p;
  int i,index,count;
  f=fopen("mapping","r");
  if (f==NULL)
    {
      fprintf(stderr,"Cannot open file \"mapping\"\n");
      exit(1);
    }
  fgets(line,4000,f);
  count=0;
  while(!feof(f))
    {
      ch=strtok(line," \t");
      index=ch[0];
      for(i=0;i<PHO_FEATURES;i++)
	{
	  ch=strtok(NULL," \t");
	  if (ch==NULL)
	    {
	      fprintf(stderr,"missing value for character %c\n",index);
	      strcpy(vector[index][i],"?");
	    }
	  else strncpy(vector[index][i],ch,5);
	  if (vector[index][i][0]=='0')
	    strcpy(vector[index][i],"0");
	}
      p=vector[index][PHO_FEATURES-1];
      if (p[strlen(p)-1]=='\n')
	p[strlen(p)-1]=0;
      fgets(line,4000,f);
    }
  fclose(f);
}


int main(int argc,char *argv[])
{
  int sem[SEM_FEATURES];
  char line[255];
  int i,j;
  FILE *f;
  char *prob_str,*orth,*pho;
  float prob,v;
  char *word;

  f=fopen("ortho.features","r");
  if (f==NULL)
    {
      fprintf(stderr,"can't open file 'ortho.features'\n");
      exit(-1);
    }
  for(i=0;i<MAX_ORTH;i++)
    for(j=0;j<26;j++)
      {
	fscanf(f,"%d",&ortho_features[i][j]);
      }

  fclose(f);

  load_mapping();

  gets(line);
  while(!feof(stdin))
    {
      word=strtok(line," \t");
      orth=strtok(NULL," \t\n");
      pho=strtok(NULL," \t\n");
      prob_str=strtok(NULL," \t\n");

      if (prob_str != NULL)
	{
	  v=atof(prob_str);
	  prob=FREQ(v);
	}

      if (prob<MIN_PROB)
        prob=MIN_PROB;
      if (prob > 1.0)
	prob=1.0;
	  
      print_it(word,orth,pho,prob,sem);
      gets(line);
    }
  return 0;
}


