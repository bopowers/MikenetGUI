#include<stdio.h>
#include<stdlib.h>


#define MAX_LETTERS 13

char words[10000][20];
int num_words=0;

char  map[MAX_LETTERS][26];

main()
{
  char line[500];
  int i,j,count;

  for(i=0;i<MAX_LETTERS;i++)
    for(j=0;j<26;j++)
      map[i][j]=0;
  
  gets(line);
  while(!feof(stdin))
    {
      strcpy(words[num_words++],line);
      gets(line);
    }
  for(i=0;i<num_words;i++)
    {
      for(j=0;j<MAX_LETTERS;j++)
	{
	  if (words[i][j]!='_')
	    map[j][words[i][j]-'a'] =1;
	}
    }

  count=0;
  for(i=0;i<MAX_LETTERS;i++)
    {
      for(j=0;j<26;j++)
	{
	  if (map[i][j])
	    printf("%d ",count++);
	  else printf("-1 ");
	}
      printf("\n");
    }
}

