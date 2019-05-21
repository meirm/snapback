#!/bin/bash


for i in $@; do ls -l $PWD/$i ; find ~/.Snapshots -name "$i"  -ls | grep $PWD | perl -ne '
BEGIN{
sub tohours{
        ($i)=@_;
        if ($i=~ m/hour-(\d+)/){
                $o=$1
        }elsif ($i=~ m/day-(\d+)/){
                $o=24*($1+1)
        }elsif ($i=~ m/week-(\d+)/){
                $o=24*7*($1+1)
        }elsif ($i=~ m/month-(\d+)/){
                $o=30*24*($1+1)   
        }
}
}
next unless m/^\s*(\d+)/; 
$seen{$1}=$_;
END{
        print $seen{$_} foreach sort {tohours($seen{$a})<=>tohours($seen{$b})}  keys %seen
}';done
