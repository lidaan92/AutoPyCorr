#!/usr/bin/perl -w
# autopycorr_v1_2080_L7.pl
#prevent disasters
use strict;
use warnings;
#perl module
use Data::Dumper;
$Data::Dumper::Indent = 1;
$Data::Dumper::Sortkeys = 1;

#################################################################################################################

print "============================================ AutoPyCorr ============================================\n";

##################################################### log file ##################################################
print "Operations will be logged in /Landsat7/logs 'Landsat7_Automation.log' +--------------------------]|>\n";

#open new file and write > (>> would open and append) $=variable
open my $fh, ">>", "/Volumes/RAID/Landsat7/logs/Landsat7_Automation.log" or die "FATAL: Could not open log!: $!\n";
print $fh "--------------------------------------------------------------------\n";
#################################################################################################################


chdir '/Volumes/RAID/Landsat7/antarctica';
system ("pwd\n");

my @dirs = grep -d, </Volumes/RAID/Landsat7/antarctica/p*_r*>;

    for my $dir (@dirs) {
      if (-d $dir) {
      
      my $raw_path = "$dir/raw";
      my $band8_path = "$dir/band8";
      chdir "$band8_path" or die "failed to cd: $!";
    
      my @dates = ();
      my @tifs = ();
      my %dates_tifs;
      
      my @tif_files = glob '*B8.TIF'; 		#all the .tifs in the current dir
        
        if (@tif_files > 1) {
          print " \n";
          print "~~~~~~~~~~~~~~~~~~~~~> $band8_path <~~~~~~~~~~~~~~~~~~~~~~~\n";
          for my $tif_file (@tif_files) {
          print "TIF FILE ::: $tif_file\n";
 	  
          my ($date) = $tif_file =~ m/^LE7\d{6}(\d+)EDC\d\d\_B8.TIF$/xms;
 	      my ($path, $row) = $tif_file =~ m/^LE7(\d{3})(\d{3})\d+EDC\d\d\_B8.TIF$/xms;
	      my $p_r = "p${path}_r${row}";
	      $date += 0;
	      print "date = $date\n";
	  
	      push(@dates, $date);
	      push(@tifs, $tif_file);
	  
	      @dates_tifs{@dates} = @tifs;
	      } #ends for my tifs
 	    } #ends if tifs

############################################### pycorr automation ################################################
	  if (@tif_files > 1) {
	    
	    print "################# FINAL HASH ##################\n";
	    print Data::Dumper->Dump([\%dates_tifs], ["Date => TIF"]), $/;    
	    print "###############################################\n";
	    
	    my $count = int(keys %dates_tifs);
	    my $number = 0;
	    while ( $count > $number ) {
	      foreach my $key (keys(%dates_tifs)) {
	      $number++;
          }
	    } 
	    for my $date1 (keys %dates_tifs) {
	      for my $date2 (keys %dates_tifs) {
		   next if $date2 < $date1;
		
		   if ( $date2 > $date1 ) {
		   print "_________________\n";
		   print "\$date2 - \$date1 |\n";
		   print $date2 - $date1, "\n";
		   print "-----------------\n";
		  
		   #my $inc20 = "-inc 20 -half_source_chip 20 -half_target_chip 80";
		  
		   print "\n";
		   print "> Correlations for $dates_tifs{$date1} & $dates_tifs{$date2} <\n";
		  
		   print "_____________________________________________________________________________\n";
           ########################### WHERE YOU ENTER PYCORR SCRIPT ##############################		  
		   print "python pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2} -imgdir $band8_path $main::parameters\n";
		   #system ("python /ENTER PATH HERE/pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2} -imgdir $band8_path $main::parameters");
		   
		   print $fh "PyCorr --> $dates_tifs{$date1} $dates_tifs{$date2} \n";  
		  } #ends for my date1
	     } #ends for my date2  
	    } #end if date2 > date1
	  } #ends if tifs
     } #ends if dir 
      else {
	  print "$dir is not a directory!\n";
	  } #ends else (if dirs)   	  		  
    } #ends for my dir
###################################################################################################
print "\n";    
print "===================================> END OF PROCESS <===================================\n";
print "             (☞ﾟヮﾟ)☞                                            ☜(ﾟヮﾟ☜)                 \n";

print $fh "______________________________>: PyCorr END :<______________________________\n";   
print $fh "\n";