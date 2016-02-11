#!/usr/bin/perl -w
use strict;
use warnings;
############################################ Log File #############################################
open my $hfh, ">>", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log" or die "FATAL: Could not open log!: $!\n";
print $hfh "|-> : Running Landsat 7 Automation for HP Filtering : <-|\n";
print $hfh "---------------------------------------------------------\n";
###################################################################################################
print "\n";
print "-------> Initiating PyCorr Automation with HP Filtering <-------\n";

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
    print "||----> No restarts parameters <----||\n";
   	goto START3;
  }
  elsif ($correct_parameters eq "q") {
   	print $hfh "|--> User quit program\n";
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
######################################### PC DIRECTORY ############################################
print "-------> Initiating PC Script <-------\n";   
print $hfh "> Running PC ENVI Script on Raw B8.TIF Files <\n";
print $hfh "----------------------------------------------\n";

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
          
          ###################################### PC with ENVI #####################################
          print "System --> PC.ENVI -> $tif_file\n";
          print $hfh "System: --> PC.ENVI -> $tif_file\n";
          # system ("/PATH TO PC SCRIPT/pc.envi") or die "FATAL: Could not run PC Script! : $!\n";
          #########################################################################################
          
          }
        }
      }
    }