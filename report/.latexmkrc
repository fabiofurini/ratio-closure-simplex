# The PDF belongs next to its sources; only LaTeX's scratch files go to build/.
$out_dir = '.';
$aux_dir = '../build/report';
$jobname = 'ratio_closure_simplex_report';
$ENV{'BIBINPUTS'} = '../latex/common:' . ($ENV{'BIBINPUTS'} // '');
