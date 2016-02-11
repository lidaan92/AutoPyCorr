#!/usr/bin/perl -w

# Unzips and untars B8.tifs from Landsat 8 scenes from /Landsat7/downloads
# And moves them to their corresponding folders in /Landsat8/antarctica/pxxx_rxxx

use strict;
use warnings;
#use Archive::Tar;
#use autodie qw/:all/;
#use File::Copy;
#################################################################################################################

print "================================= Moving Landsat8 downloaded files ================================\n";

##################################################### log file ##################################################
print "Operations will be logged in /Landsat8/logs 'move_L8dl.log' +-----------------------------------]|>\n";
open my $fh, ">>", "/Volumes/RAID/Landsat8/logs/move_L8dl.log" or die "FATAL: Could not open log!: $!\n";
print $fh "=========================================================================================\n";
my $date_string = localtime;  # e.g., "Thu Oct 13 04:54:34 1994"
print $fh "$date_string\n";
print $fh "++++++++++++++++++++++++\n";
#################################################################################################################


chdir "/Volumes/RAID/Landsat8/downloads" or die "FATAL: failed to cd!: $!";

system ("rm -v *\\(1\\)*");    #removes all duplicates in directory

#open(STDERR, '>>', "/Volumes/RAID/Landsat8/logs/move_error.log") or die "failed to open move_error.log!: $!";

my @files     = glob "*.*";
my @tar_files = glob '*.tar.gz'; # All the tar files in the curr dir.
my @jpg_files = glob '*.jpg'; # All the .jpg files in the curr dir.

unless (@files) {
    die "x========(▀̿̿Ĺ̯̿̿▀̿ ̿)=========> No files here. Exiting! <=========(▀̿̿Ĺ̯̿̿▀̿ ̿)==================x\n";
}

for my $tar_file (@tar_files) {
    my ($path, $row) = $tar_file =~ m/^LC8(\d{3})(\d{3})\d+LGN\d\d\.tar.gz$/xms;
    my ($scene) = $tar_file =~ m/^(\w+).tar.gz$/xms;
    
    print "Landsat Scene $scene\n";
    print "Found $tar_file, with path $path, and row $row\n";
    system ("chmod 775 $tar_file");
    print "--> chmod 775 $tar_file\n";
############################################# path variables #################################################    
    my $dir = "p${path}_r${row}";
    print "...so... directory is /$dir\n";
    
    my $dirpath = "/Volumes/RAID/Landsat8/antarctica/$dir";
    my $raw_path = "$dirpath/raw";
    my $band8_path = "$dirpath/band8";
##############################################################################################################   
    if (-d $dirpath) {
        print "... and $dir exists!\n";
        print "...with PATH::--> $dirpath\n";
    } else {
        mkdir $dirpath, 0775 or die "FATAL: FAILED to create $dirpath\n";
        mkdir $raw_path, 0775 or die "FATAL: FAILED to create $raw_path\n";
        mkdir $band8_path, 0775 or die "FATAL: FAILED to create $band8_path\n";
        print "... $dir does not exist, so making directory ...\n";
        print "...with PATH::--> $dirpath\n";
        print "...also creating dir '/raw'\n";
        print "...also creating dir '/band8'\n"; 
        print $fh "Created dir :: $dirpath\n";
        print $fh "Created dir :: $raw_path\n";
        print $fh "Created dir :: $band8_path\n";
    }
    
    {
     system ("mv -v $tar_file $raw_path") == 0 or die "FATAL: Can't move file!";
     print "moved $tar_file to /$dir/raw\n";
     print $fh "--> moved $tar_file to $raw_path\n";
    }
    {
     chdir "$raw_path" or die "FATAL: Can't cd to /$dir/raw !\n";
     print "...changing to /$dir/raw...\n";
     system ("pwd\n");
    }
    {
     print "-------------------------------:Current Contents:---------------------------------------------\n";
     system ("ls -G\n");
     print "______________________________________________________________________________________________\n";
     
     my $b8 = "_B8.TIF";
     my $tif = "$scene$b8";  
     print "TIF::$tif\n";
################################################## tar #######################################################     
     if (system ("tar -xzvf $tar_file $tif") == 0) {
	print "...untaring... please wait...\n";
	system ("tar -xzvf $tar_file $tif");
	print $fh "Unpacked $tar_file\n";
	system ("mv -v $tif $band8_path") == 0 or die "FATAL: Failed to move $tif to $band8_path\n";
	print $fh "--> Moved $tif to $band8_path\n"
     } else {
      print "unpacking of $tar_file failed!\n";
      print "logging missing $tif to missing_b8.log in '/Landsat8/logs'\n";
      open my $b8fh, ">>", "/Volumes/RAID/Landsat8/logs/missing_b8.log";
      print $b8fh "----------------------------\n";
      print $b8fh "$tif\n";
      print $b8fh "$raw_path";
      close $b8fh;
      print $fh ":: Logged missing $tif to missing_b8.log ::\n";
      }
 #############################################################################################################    
     print "-----------------------------------:New Contents:---------------------------------------------\n";
     system ("ls -G\n");
     print "______________________________________________________________________________________________\n";
     print "...moving on...\n";
    }
    {
     chdir "/Volumes/RAID/Landsat8/downloads";
     print "-------------------------- Remaining tars in /Landsat8/downloads -----------------------------\n";
     system ("ls -G *.tar*\n");
     print "______________________________________________________________________________________________\n";
    }
}

print "================= tar files done! ======ᕕ( ͡° ͜ʖ ͡°)ᕗ======...now jpgs...=============================\n";

for my $jpg_file (@jpg_files) {
    my ($path, $row) = $jpg_file =~ m/^LC8(\d{3})(\d{3})\d+LGN\d\d\.jpg$/xms;
    my ($scene) = $jpg_file =~ m/^(\w+).jpg$/xms;
    
    print "Landsat Scene  $scene\n";
    print "Found $jpg_file, with path $path, and row $row\n";
######################################### path variables #####################################################    
    my $dir = "p${path}_r${row}";
    my $dirpath = "/Volumes/RAID/Landsat8/antarctica/$dir";
    my $raw_path = "$dirpath/raw";
    my $band8_path = "$dirpath/band8";
    
    print "...so...dir is /$dir\n";
##############################################################################################################    
    
    system ("chmod 775 $jpg_file");
    print ">chmod 775 $jpg_file\n";
    
    if (-d $dirpath) {
        print "... and $dir exists!\n";
        print "...with PATH::--> $dirpath\n";
    } else {
        mkdir $dirpath, 0775 or die "FATAL: FAILED to create $dirpath\n";
        mkdir $raw_path, 0775 or die "FATAL: FAILED to create $raw_path\n";
        mkdir $band8_path, 0775 or die "FATAL: FAILED to create $band8_path\n";
        print "$dir does not exist, so making directory...\n";
        print "...with PATH::--> $dirpath\n";
        print "...also creating dir '/raw'\n";
        print "...also creating dir '/band8'\n"; 
        print $fh "Created dir :: $dirpath\n";
        print $fh "Created dir :: $raw_path\n";
        print $fh "Created dir :: $band8_path\n";
      }
      
    system ("mv -v $jpg_file $raw_path") == 0 or die "Failed to move $jpg_file\n";
	print "Moved jpg to $raw_path\n";
	print $fh "--> Moved $jpg_file to $raw_path\n";
    chdir "/Volumes/RAID/Landsat8/downloads";
     print "-------------------------- Remaining jpgs in /Landsat8/downloads -----------------------------\n";
     system ("ls -G\n");
     print "______________________________________________________________________________________________\n";
	
      
}
print $fh "_______________________________ end of run ____________________________________________\n";   
close $fh;

print "(ง ͠° ͟ل͜ ͡°)ง \n";

print "===+===+======+===+======+===+======+===+======+===+======+===+======+===+======+===+======+===+===\n";
print "-( ͡° ͜ʖ ͡°)--It's been a long battle ... but I think most of us made it out alive------- ( ͡° ͜ʖ ͡°)----\n";
print "^*===><===**===><===*===><===**===><===*===><===*^*===><===*===><===**===><===*===><===**===><===*^\n";