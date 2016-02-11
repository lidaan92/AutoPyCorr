#!/usr/bin/perl -w


use strict;
use warnings;

print "================================= Cleanup Starting with Landsat8 ======================================\n";

print "Operations will be logged in /Landsat8/logs +--------------------------------------------------------||\n";
open my $fh, ">", "/Volumes/RAID/Landsat8/logs/cleanup_landsats.log" or die "FATAL: Could not open log!: $!\n";

print $fh "=========================================================================================\n";
my $date_string = localtime;  # e.g., "Thu Oct 13 04:54:34 1994"
print $fh "$date_string\n";
print $fh "++++++++++++++++++++++++\n";

chdir '/Volumes/RAID/Landsat8/antarctica';
system ("pwd\n");

my @dirs = grep -d, </Volumes/RAID/Landsat8/antarctica/p*_r*>;

  for my $dir (@dirs) {
      if (-d $dir) {
      
      print "--> $dir\n";
      chdir "$dir" or die "failed to cd: $!\n";
      system ("pwd\n");
      
      print ":::::::::::::::::::::::::::::::: LISTING CONTENTS :::::::::::::::::::::::::::::::::::::::::::::::\n";
      system ("ls -G\n");
      print "_________________________________________________________________________________________________\n";
      
      my @tar_files = glob '*.tar.gz'; # All the tar files in the curr dir.
      
	if (@tar_files) {
 	  for my $tar_file (@tar_files) {
     
 	  print "TAR FILE:::$tar_file\n";
 	  system ("mv -v $tar_file raw/") == 0 or die "FATAL: Failed to move $tar_file into '/band8' : $!\n";
 	  print "---> moved $tar_file into /raw\n";
 	  print $fh "---> moved $tar_file into $dir/raw\n";	  
	  }
	print "::::::: Current Files in $dir/raw ::::::::\n";
	system ("ls -G raw/\n");
	print "_______________________________________________________________________________________________\n";
	}
      
      my @tif_files = glob '*.TIF'; 		#all the .tifs in the current dir
  	
 	if (@tif_files) {
 	  for my $tif_file (@tif_files) {
     
 	  print "TIF FILE:::$tif_file\n";
 	  system ("mv -v $tif_file band8/") == 0 or die "FATAL: Failed to move $tif_file into '/band8' : $!\n";
 	  print "---> moved $tif_file into /band8\n";
 	  print $fh "---> moved $tif_file into $dir/band8\n";
 	  }
 	}
      print "::::::: Current Files in $dir/band8 ::::::::\n";
      system ("ls -G band8/\n");
      print "_________________________________________________________________________________________________\n";
      my @jpg_files = glob '*.jpg'; # All the .jpg files in the curr dir.
      
	if (@jpg_files) {
 	  for my $jpg_file (@jpg_files) {
     
 	  print "JPG FILE:::$jpg_file\n";
 	  system ("mv -v $jpg_file raw/") == 0 or die "FATAL: Failed to move $jpg_file into '/band8' : $!\n";
 	  print "---> moved $jpg_file into /raw";
 	  print $fh "---> moved $jpg_file into $dir/raw\n";
	  }
      print "::::::: Current Files in $dir/raw ::::::::\n";
      system ("ls -G raw/\n");
      print "_________________________________________________________________________________________________\n";
	}
      
      ####################### Moving tifs inside /raw ###########################################################
      chdir "$dir/raw" or die "FATAL: FAiled to chdir to /raw/ : $!\n";
      my @tif_files = glob '*.TIF'; 		#all the .tifs in the current dir
  	
 	if (@tif_files) {
 	  for my $tif_file (@tif_files) {
     
 	  print "TIF FILE:::$tif_file\n";
 	  system ("mv -v $tif_file $dir/band8/") == 0 or die "FATAL: Failed to move $tif_file into '/band8' : $!\n";
 	  print "---> moved $tif_file into /band8\n";
 	  print $fh "---> moved $tif_file from $dir/raw into $dir/band8\n";
 	  }
 	}
    }
  }
print $fh "_______________________________ end of run ____________________________________________\n";   
close $fh;
  
print "==================================== Cleanup Now With Landsat7 ========================================\n";

print "Operations will be logged in /Landsat7/logs +--------------------------------------------------------||\n";
open my $fh, ">", "/Volumes/RAID/Landsat7/logs/cleanup_landsats.log" or die "FATAL: Could not open log!: $!\n";

print $fh "=========================================================================================\n";
my $date_string = localtime;  # e.g., "Thu Oct 13 04:54:34 1994"
print $fh "$date_string\n";
print $fh "++++++++++++++++++++++++\n";

chdir '/Volumes/RAID/Landsat7/antarctica';
system ("pwd\n");

my @dirs = grep -d, </Volumes/RAID/Landsat7/antarctica/p*_r*>;

  for my $dir (@dirs) {
      if (-d $dir) {
      
      print "--> $dir\n";
      chdir "$dir" or die "failed to cd: $!";
      system ("pwd\n");
      
      print ":::::::::::::::::::::::::::::::: LISTING CONTENTS :::::::::::::::::::::::::::::::::::::::::::::::\n";
      system ("ls -G\n");
      print "_________________________________________________________________________________________________\n";
      
      my @tar_files = glob '*.tar.gz'; # All the tar files in the curr dir.
      
	if (@tar_files) {
 	  for my $tar_file (@tar_files) {
     
 	  print "TAR FILE:::$tar_file\n";
 	  system ("mv -v $tar_file raw/") == 0 or die "FATAL: Failed to move $tar_file into '/band8'\n";
 	  print "---> moved $tar_file into /raw\n";
 	  print $fh "---> moved $tar_file into /raw\n";
	  }
	print "::::::: Current Files in $dir/raw ::::::::\n";
	system ("ls -G raw/\n");
	print "_______________________________________________________________________________________________\n";
	}
      
      my @tif_files = glob '*.TIF'; 		#all the .tifs in the current dir
  	
 	if (@tif_files) {
 	  for my $tif_file (@tif_files) {
     
 	  print "TIF FILE:::$tif_file\n";
 	  system ("mv -v $tif_file band8/") == 0 or die "FATAL: Failed to move $tif_file into '/band8'\n";
 	  print "---> moved $tif_file into /band8\n";
 	  print $fh "---> moved $tif_file into /band8\n";
 	  }
 	}
      print "::::::: Current Files in $dir/band8 ::::::::\n";
      system ("ls -G band8/\n");
      print "_________________________________________________________________________________________________\n";
      my @jpg_files = glob '*.jpg'; # All the .jpg files in the curr dir.
      
	if (@jpg_files) {
 	  for my $jpg_file (@jpg_files) {
     
 	  print "JPG FILE:::$jpg_file\n";
 	  system ("mv -v $jpg_file raw/") == 0 or die "FATAL: Failed to move $jpg_file into '/band8'\n";
 	  print "---> moved $jpg_file into /raw\n";
 	  print $fh "---> moved $jpg_file into /raw\n";
	  }
      print "::::::: Current Files in $dir/raw ::::::::\n";
      system ("ls -G raw/\n");
      print "_________________________________________________________________________________________________\n";
	}
      
      ####################### Moving tifs inside /raw ###########################################################
      chdir "$dir/raw" or die "FATAL: FAiled to chdir to /raw/ : $!\n";
      
      my @tif_files = glob '*.TIF'; 		#all the .tifs in the current dir
  	
 	if (@tif_files) {
 	  for my $tif_file (@tif_files) {
     
 	  print "TIF FILE:::$tif_file\n";
 	  system ("mv -v $tif_file $dir/band8/") == 0 or die "FATAL: Failed to move $tif_file into '/band8' : $!\n";
 	  print "---> moved $tif_file into /band8\n";
 	  print $fh "---> moved $tif_file from $dir/raw into /band8\n";
 	  }
 	}
    }
  }
print $fh "_______________________________ end of run ____________________________________________\n";  
close $fh;  

print "  \n"; 
print "============================================ FINISHED ===========================================\n";
print "**********************^^^****************** (ง ͠° ͟ل͜ ͡°)ง *******************^^^^^^******************\n";
