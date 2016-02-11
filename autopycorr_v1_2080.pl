#!/usr/bin/perl -w
#prevent disasters
use strict;
use warnings;
#perl module
use Data::Dumper;
$Data::Dumper::Indent = 1;
$Data::Dumper::Sortkeys = 1;

#How it procedurally enters all directories;
#################################################################################################################

print "============================================= AutoPyCorr ============================================\n";

##################################################### log file ##################################################
print "Operations will be logged in /Landsat8/logs 'auto_pycorr.log' +---------------------------------]|>\n";

#open new file and write > (>> would open and append) $-variable
open my $fh, ">", "/Volumes/RAID/Landsat8/logs/auto_pycorr.log" or die "FATAL: Could not open log!: $!\n";
print $fh "=========================================================================================\n";
my $date_string = localtime;  # e.g., "Thu Oct 13 04:54:34 1994"
print $fh "$date_string\n";
print $fh "++++++++++++++++++++++++\n";
#################################################################################################################

chdir '/data2/jennb/landsat8/antarctica';

system ("pwd\n");

my @dirs = grep -d, </Volumes/RAID/Landsat8/antarctica/p*_r*>;

    for my $dir (@dirs) {
      if (-d $dir) {
      
      my $raw_path = "$dir/raw";
      my $band8_path = "$dir/band8";
      
      print " \n";
      print "~~~~~~~~~~~~~~~~~~~~~> $band8_path <~~~~~~~~~~~~~~~~~~~~~~~\n";
      print $fh "~~~~~~~~~~~> $band8_path <~~~~~~~~~~~\n";
      
      chdir "$band8_path" or die "failed to cd: $!";
     
      #system ("pwd\n");
      print " \n";
      print "------------------------------------|Current Contents|-------------------------------------------\n";
      print "                                                                                                 \n";
      system ("ls -G\n");
      print "-------------------------------------------------------------------------------------------------\n";
     
      my @dates = ();
      my @tifs = ();
      my %dates_tifs;
      
      
      #chdir "$band8_path" or die "FATAL: Failed to cd to $band8_path: $!";
      
      my @tif_files = glob '*B8.TIF'; 		#all the .tifs in the current dir
  	
        if (@tif_files) {
          for my $tif_file (@tif_files) {
     
          print "TIF FILE ::: $tif_file\n";
 	  
          my ($date) = $tif_file =~ m/^LC8\d{6}(\d+)LGN\d\d\_B8.TIF$/xms;
 	      my ($path, $row) = $tif_file =~ m/^LC8(\d{3})(\d{3})\d+LGN\d\d\_B8.TIF$/xms;
	      my $p_r = "p${path}_r${row}";
	      print "$p_r\n";
	      $date += 0;
	      print "date = $date\n";
	  
	      push(@dates, $date);
	      push(@tifs, $tif_file);
	  
	      @dates_tifs{@dates} = @tifs;
	  
	      print "################ BUILDING HASH ################\n";
	      print Data::Dumper->Dump([\%dates_tifs], ["Date => TIF"]), $/;
	      print "###############################################\n";
	  
	  
  
	      } #ends for my tifs
 	    } #ends if tifs
 	else {
	    print "...no band8s here... --> next dir... \n";
	    print $fh "...no band8s here...\n";
	    print $fh "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n";
 	} #ends else (if tifs)
############################################### pycorr automation ################################################
	  
	  if (@tif_files) {
	    
	    print "################# FINAL HASH ##################\n";
	    print Data::Dumper->Dump([\%dates_tifs], ["Date => TIF"]), $/;    
	    print "###############################################\n";
	    
	    ############################ log file ############################
	    #print $fh " \n";
	    #print $fh "################ FINAL HASH #################\n";
	    #print $fh Data::Dumper->Dump([\%dates_tifs], ["Date => TIF"]), $/;
	    #print $fh "#############################################\n";
	    ##################################################################
	    
	    my $count = int(keys %dates_tifs);
	    print "There are $count elements in the hash\n";
	    #$count += 0;
	    #print "Count up: " , (1 .. $count), "\n";
	  
	    my $number = 0;
	  
	    
	    foreach my $key (keys(%dates_tifs)) {
	      while ( $count > $number ) {
	  
	      $number++;
	      
	      print "date_$number = $key\n";
	      }
	      
	      
	      
	      
	      #print $key - each(@dates), "\n";
	    
	    }
	    
	    
	    for my $date1 (keys %dates_tifs) {
	      for my $date2 (keys %dates_tifs) {
		next if $date2 < $date1;
		
		if ( $date2 > $date1 ) {
		  print "_________________\n";
		  print "\$date2 - \$date1 |\n";
		  print $date2 - $date1, "\n";
		  print "-----------------\n";
		  
		  my $inc20 = "-inc 20 -half_source_chip 20 -half_target_chip 80";
	          my $inc16 = "-inc 16 -half_source_chip 16 -half_target_chip 80";
                  my $inc24 = "-inc 24 -half_source_chip 24 -half_target_chip 96";
		  
		  print "\n";
		  print "> Correlations for $dates_tifs{$date1} & $dates_tifs{$date2} <\n";
		  
		  print "________________________________________________________________________________\n";
		  
            #print "python pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2}
            #-vf -sf -v
            #-imgdir $band8_path
            #-nsidc_out_names -use_hp -gfilt_sigma 3.0
            #$inc16 \n\n";
		  
		  print "python pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2}
		  -vf -sf -v 
		  -imgdir $band8_path 
		  -nsidc_out_names -use_hp -gfilt_sigma 3.0 -kmz -log10
		  $inc20 \n\n";
          
            system ("python /Users/klinger/Desktop/pycorr_versions/pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2} -vf -sf -v -imgdir $band8_path -nsidc_out_names -use_hp -gfilt_sigma 3.0 -kmz -log10 $inc20");
            
		  
            #print "python pycorr_v1.06.py $dates_tifs{$date1} $dates_tifs{$date2}
            # -vf -sf -v
            #-imgdir $band8_path
            #-nsidc_out_names -use_hp -gfilt_sigma 3.0
            #$inc24 \n\n";
		  
		  print $fh "\n";
		  print $fh "\$ pycorr --> $dates_tifs{$date1} $dates_tifs{$date2} \n";  
		
		
		#print "$delt\n";
		
		
		}
	      }
	      
	    }
	  
##################################################################################################################	  
############################################### log file #########################################################	  
	  #print $fh "-----------\n";
	  #print $fh "$p_r |\n";
	  
	  
	  
	  
	  print $fh "\n";
	  print $fh "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n";
	  
##################################################################################################################
	  
	  } #ends if tifs
       print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~\n";
      } #ends if dir 
      else {
	  print "$dir is not a directory!\n";
	  } #ends else (if dirs)   	  
 		  
    } #ends for my dir
    
print "====================================> END OF PROCESS <====================================\n";
print "             (☞ﾟヮﾟ)☞                                             ☜(ﾟヮﾟ☜)                 \n";
print "==========================================================================================\n";

print $fh "_______________________________ end of run ____________________________________________\n";   
close $fh;
	  

      	
 	
      



    




