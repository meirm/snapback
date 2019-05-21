#!/bin/bash
PERIOD=$1;
(( PERIOD = PERIOD + 1 ))
shift;

#for i in $@; do vimdiff $i  ~/.Snapshots/$PERIOD/$PWD/$i ;done
vimdiff $1 `snapls.sh $1 | head -n $PERIOD | tail -1 | perl -ne 'chomp;s/.*\s+//;print "$_\n"'`
