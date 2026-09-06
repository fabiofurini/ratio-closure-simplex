# The PDF belongs next to its sources; only LaTeX's scratch files go to build/.
$out_dir = '.';
$aux_dir = '../build/tutorial';
$jobname = 'ratio_closure_simplex_tutorial';
$ENV{'BIBINPUTS'} = '../latex/common:' . ($ENV{'BIBINPUTS'} // '');
