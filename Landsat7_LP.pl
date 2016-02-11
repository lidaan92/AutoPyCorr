#!/usr/bin/perl -w
use strict;
use warnings;
############################################ Log File #############################################
print "Operations will be logged in /Landsat7/logs 'Landsat7_Automation.log' +------ --------]|>\n";
open my $lfh, ">>", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log" or die "FATAL: Could not open log!: $!\n";
print $lfh "|-> : Running Landsat 7 Automation for HP Filtering : <-|\n";
print $lfh "---------------------------------------------------------\n";
###################################################################################################
print "\n";
print "-------> Initiating PyCorr Automation with LP Filtering <-------\n";

START2:
print "Default parameters are: -vf -sf -v -nsidc_out_names -use_hp -gfilt_sigma 3.0 -inc20 -half_source20" ,
  " -half_target20\n";
print "Would you like to use the default? (y/n)> ";
my $default = <>;
chomp $default; 
if ($default eq "y") {
  print "Good choice!\n";
  $main::parameters = "-vf -sf -v -nsidc_out_names -use_hp -gfilt_sigma 3.0 -inc20 -half_source20";
}
elsif ($default eq "n") {
  START3:
  print "Here are the parameter options:\n";
  print "-img1datestr -img2datestr -datestrfmt -img1_name -img2_name -out_name_base\n" ,
    "-bbox -plotvmin -plotvmax -plot_2_mult -half_source_chip -half_target_chip -inc\n" ,
   	"-gfilt_sigma -gs_min -gs_max -dcam -cam -cam1 -alphaval -of -v -vf -mpy -kmz -log10\n" ,
   	"-no_gtif -use_hp -only_vel_colormap -nlf -npb -sf -pixfigs -nsidc_out_names\n";
  print "Please enter the EXACT parameters you wish to use for PyCorr:\n";
  print "> ";
  $main::parameters = <>;
  chomp $main::parameters;
  print "You wish to run PyCorr with these parameters:\n";
  print "$main::parameters\n";
  START4:
  print "Correct? (y/n/q)> ";
  my $correct_parameters = <>;
  chomp $correct_parameters;
  if ($correct_parameters eq "y") {
   	print "----> Running PyCorr with these parameters: \n";
   	print "$main::parameters\n";
  }
  elsif ($correct_parameters eq "n") {
   	print "||----> No restarts program <----||\n";
   	goto START3;
  }
  elsif ($correct_parameters eq "q") {
   	print $lfh "|--> User quit program\n";
   	print "||----> User selected quit; Exiting!\n";	
   	exit 0;
  }
  else {
    goto START4;
  }
}
else {
  goto START2;
}
######################################### PC DIRECTORIES ##########################################
print "-------> Initiating PC Script <-------\n";   
print $lfh "> Running PC ENVI Script on Raw B8.TIF Files <\n";
print $lfh "----------------------------------------------\n";

my @pcdirs = grep -d, </Volumes/RAID/Landsat7/antarctica/p*_r*>;

    for my $dir (@pcdirs) {
      if (-d $dir) {
      my $band8_path = "$dir/band8";
      chdir "$band8_path" or die "failed to cd: $!";
      
      my @tif_files = glob '*B8.TIF'; 		#all the .tifs in the current dir
  	
        if (@tif_files) {
          print " \n";
          print "~~~~~~~~~~~~~~~~~~~~~> $band8_path <~~~~~~~~~~~~~~~~~~~~~~~\n";
          for my $tif_file (@tif_files) {
     
          print "TIF FILE ::: $tif_file\n";
          
          ###################################### PC Script #####################################
          print "system --> PC.ENVI -> $tif_file\n";
          print $lfh "system: --> PC.ENVI -> $tif_file\n";
          # system ("/PATH TO PC SCRIPT/pc.envi") or die "FATAL: Could not run PC Script! : $!\n";
          #########################################################################################
          
          }
        }
      }
    }
print $lfh "----------------------------------------------\n";
########################################## LP DIRECTORIES #########################################
print "-------> Generating LP & HP Geotifs <-------\n";  
print $lfh "> Generating LP & HP Geotifs on PC.TIF Files <\n";
print $lfh "----------------------------------------------\n";

my @lpdirs = grep -d, </Volumes/RAID/Landsat7/antarctica/p*_r*>;

    for my $dir (@lpdirs) {
      if (-d $dir) {
      
      my $band8_path = "$dir/band8";
      
      chdir "$band8_path" or die "failed to cd: $!";
      
      my @tif_files = glob '*B8.TIF'; 		#all the .tifs in the current dir
  	
        if (@tif_files) {
          print " \n";
          print "~~~~~~~~~~~~~~~~~~~~~> $band8_path <~~~~~~~~~~~~~~~~~~~~~~~\n";
          
          for my $tif_file (@tif_files) {
            print "TIF FILE ::: $tif_file\n";
          
            ################################## LP SCRIPT ##########################################
            print "System: --> generate_lp_hp_geotifs_v1.0mk.py $tif_file\n";
            print $lfh "System: --> generate_lp_hp_geotifs_v1.0mk.py $tif_file\n";
            # system ("python /PATH TO SCRIPT/generate_lp_hp_geotifs_v1.0mk.py $tif_file") or die "FATAL: Could not run .py script! $!\n";
            #######################################################################################
          }
        }
      }
    }