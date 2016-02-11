#!/usr/bin/perl -w
use strict;
use warnings;
#perl module
use Data::Dumper;
$Data::Dumper::Indent = 1;
$Data::Dumper::Sortkeys = 1;
############################################ Log File #############################################
print "+--------------]> Operations will be logged in /Landsat7/logs 'Landsat7_Automation.log'\n";
open my $afh, ">", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log" or die "FATAL: Could not open log!: $!\n";
print $afh "=============================================================================\n";
my $date_string = localtime;  # e.g., "Thu Oct 13 04:54:34 1994"
print $afh "$date_string\n";
print $afh "++++++++++++++++++++++++\n";
###################################################################################################

print $afh "|]+++======*=======> ^*^ +:+ LANDSAT 7 AUTOMATION +:+ ^*^ <========*====+++[|\n";
print $afh "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n";
# Autoflush procedure to force print to log file.
# It is a buffering problem, just for the log file
my $oldfh = select( $afh ); 
$|++; 
select( $oldfh );

###################################### LANDSAT 7 AUTOMATION #######################################

print "\n";
print "|]+++===================> ^*^ +:+ LANDSAT 7 AUTOMATION +:+ ^*^ <===================+++[|\n";
print "^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^\n";
our $parameters;
#user inputs for hp or lp
print "\n";
START1:
print "Are we doing hp or lp? (hp/lp) (q = quit) > ";
my $answer = <>;
chomp $answer;

if ($answer eq "hp") {
   #################################### If Doing HP Filter ########################################
   do "/Volumes/RAID/Landsat7/scripts/Landsat7_HP.pl" == 0 or die "FATAL:Error running Landsat7_HP.pl $!\n";
   ################################################################################################ 
}
elsif ($answer eq "lp") {
   #################################### If Doing LP Filter ########################################
   do "/Volumes/RAID/Landsat7/scripts/Landsat7_LP.pl" == 0 or die "FATAL:Error running Landsat7_LP.pl : $!\n";
   ################################################################################################ 
}
elsif ($answer eq "q") {
	print $afh "|--> User quit program\n";
	die "||----> User selected quit, exiting program!\n";
}
else {
  print "Please select 'hp' or 'lp' \n";
  goto START1;
}

# path and row numbers?

###################################################################################################
open my $nafh, ">>", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log";
###################################################################################################
############################################ AutoPyCorr ###########################################

print "Running PyCorr with $parameters\n";
print $nafh "---------------------------------------------------\n";
print $nafh "Running autopycorr_v1_2080_L7_inputs.pl\n";
print $nafh "With parameters:\n";
print $nafh "$parameters\n";
my $yoldfh = select( $nafh ); #autoflush
$|++; #
select( $yoldfh ); #

do "/Volumes/RAID/Landsat7/scripts/autopycorr_v1_2080_L7_inputs.pl";

###################################################################################################
open my $efh, ">>", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log"; 
print $efh "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n";
print $efh "________________________ END OF LANDSAT 7 AUTOMATION _______________________\n";
my $eoldfh = select( $efh ); #autoflush
$|++; #
select( $eoldfh ); #

print "++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++\n";
print "<-----------*------------> : LANDSAT 7 AUTOMATION COMPLETED : <------------*----------->\n";
###########
close $afh;
close $efh;
close $nafh;