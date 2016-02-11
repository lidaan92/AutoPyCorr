#!/usr/bin/perl -w


use strict;
use warnings;

chdir '/Volumes/RAID/Landsat8/antarctica';

my @dirs = grep -d, </Volumes/RAID/Landsat8/antarctica/p*_r*>;

  for my $dir (@dirs) {
      if (-d $dir) {
      
      print "--> $dir\n";
      chdir "$dir" or die "failed to cd: $!";
      system ("pwd\n");
      
      if (! -d 'band8') {
	    print "making directory '/band8'\n";
	    mkdir "band8", 0775;
	}
	    
	if (! -d 'raw') {
	  print "making directory '/raw'\n";
	  mkdir "raw", 0775;
        }
      
      
      print ":::::::::::::::::::::::::::::::: LISTING CONTENTS :::::::::::::::::::::::::::::::::::::::::::::::\n";
      system ("ls\n");
      print "-------------------------------------------------------------------------------------------------\n";
      
      }
      
  }