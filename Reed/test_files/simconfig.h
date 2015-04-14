#define SAMPLES 12
#define TICKS SAMPLES
#define SECONDS 4
#define INIT_GAP_TIME 4
#define HOLD_TIME 15
#define GAP_TIME 7

#define PHO_FEATURES 25
#define PHO_SLOTS 10
#define MAX_FREQ 2645809
#define ORTHO_FEATURES 110
#define PROB_MAX 30000.0

#define MIN_PROB 0
/* #define MIN_PROB 0.01  */
#define MAX_PROB 1

#define FREQ(v) sqrt(v)/sqrt(10000)
/*#define FREQ(v) (log(v+1)/log(373123)) */


#define READ_SEM_TARGET_ON 2
#define SEM_FEATURES 1989
