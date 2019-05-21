#!/bin/bash

export TARGETBASE=~/.Snapshots
#
# Number of hourly snaps:
export hsnaps=23
#Number of days to keep snaps:
export dsnaps=7
#Number of weeks to keep snaps:
export wsnaps=4
#Number of months to keep snaps:
export msnaps=12

function hourly {
	snapremount rw;
	rm -rf $TARGETBASE/hour-$hsnaps
	for i in `seq 2 $hsnaps | tac`;do
		(( next = i - 1 ))
		mv $TARGETBASE/hour-$next $TARGETBASE/hour-$i
	done
	cp -al $TARGETBASE/hour-0 $TARGETBASE/hour-1
	for SOURCE in $DIRS; do
		mkdir -p $TARGETBASE/hour-0/$SOURCE;
		rsync -av --delete $RSYNC_PARAMS $RSYNCPARAMS $SOURCE/. $TARGETBASE/hour-0/$SOURCE/.
	done
	snapremount ro;

}

function monthly {
	snapremount rw;
	rm -rf $TARGETBASE/month-$msnaps
	for i in `seq 1 $msnaps | tac`;do
		(( next = i - 1 ))
		mv $TARGETBASE/month-$next $TARGETBASE/month-$i
	done
	mv $TARGETBASE/week-$wsnaps $TARGETBASE/month-0
	snapremount ro;
}

function daily {
	snapremount rw;
	rm -rf $TARGETBASE/day-$dsnaps
	for i in `seq 1 $dsnaps | tac`;do
		(( next = i - 1 ))
		mv $TARGETBASE/day-$next $TARGETBASE/day-$i
	done

	cp -al $TARGETBASE/hour-$hsnaps $TARGETBASE/day-0
	snapremount ro;
}

function weekly {
	snapremount rw;
	rm -rf $TARGETBASE/week-$wsnaps
	for i in `seq 1 $wsnaps | tac`;do
		(( next = i - 1 ))
		mv $TARGETBASE/week-$next $TARGETBASE/week-$i
	done
	mv $TARGETBASE/day-$dsnaps $TARGETBASE/week-0
	snapremount ro;
}


function printusage {
	DIRS=~/Documents;
	TARGETBASE=~/.Snapshots;
	echo "$0"
	echo "Usage:"
	echo 
	echo $0
	echo $0 --init
	echo $0 --hourly
	echo $0 --daily
	echo $0 --weekly
	echo $0 "--help|-h"
	echo $0 "--sampleconfig"
	echo
	echo "Crontab"
	echo '# m h dom mon dow command'
	echo '0 * * * * ' $0 --hourly '>/dev/null 2>&1'
	echo '58 23 * * * ' $0 --daily '>/dev/null 2>&1'
	echo '56 22 * * 1 ' $0 --weekly '>/dev/null 2>&1'
	echo '0 1 1 * * ' $0 --monthly '>/dev/null 2>&1'
	echo
	echo
	echo $0 "--help|-h"
	echo $0 "--sampleconfig"
	echo
}

function sampleconfig {
	echo "# cat ~/.snapshotrc"
	echo "DIRS='$DIRS'"
	echo "TARGETBASE='$TARGETBASE'"
	echo "RSYNC_PARAMS='--max-size=1.5m'"
}

if [ -f ~/.snapshotrc ]; then
	source	~/.snapshotrc
else
	printusage ;
	exit 1;
fi
function snapremount {
	true # mount -o remount,$1 $TARGETBASE
}
while [ $# -gt 0 ];  do # {
case $1 in
	--conf) 
	source $2
	;;
	--rw)
	snapremount rw;
	;;
	--ro)
	snapremount ro;
	;;
	--delete)
	snapremount rw;
	SOURCE=$2
	if [ -d "$TARGETBASE/hour-0/$SOURCE" ] ; then 
		rm -rf $TARGETBASE/hour-0/$SOURCE;
	else
		echo "ERROR: could not find path $TARGETBASE/hour-0/$SOURCE";
		exit 1;
	fi
	snapremount ro;
	;;
	--init)
	snapremount rw;
	for mydir in `seq 0 $hsnaps`;do  mkdir -p $TARGETBASE/hour-$mydir;done
	for mydir in `seq 0 $dsnaps`;do  mkdir -p $TARGETBASE/day-$mydir;done
	for mydir in `seq 0 $wsnaps`;do  mkdir -p $TARGETBASE/week-$mydir;done
	for mydir in `seq 0 $msnaps`;do  mkdir -p $TARGETBASE/month-$mydir;done
	snapremount ro;
	;;	
	--hourly)
	hourly ;
	;;
	--daily)
	daily ;
	;;
	--weekly)
	weekly ;
	;;
	--monthly)
	monthly ;
	;;
	--sampleconfig|-s)
	sampleconfig
	;;
	--help|-h)
	printusage
	;;
	*)
	printusage
	;;
esac
shift  # @ARGV
done # } end while
