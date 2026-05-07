# FLUKA-Tools
This repository serves to provide some tools to make using the FLUKA general purpose Monte Carlo particle transport code a bit more user-friendly, efficient, and less error-prone.



## Output processing automation 

(To be developed. The general idea is to be able to automate execution of the various post-processing scripts distributed with FLUKA that combine results from different runs, automatically selecting which scripts to apply to which outputs based on the unit numbers assigned to them in the input file.  Beyond that, it would be nice to somehow reformat this data further into something similar to that used by [PHITS Tools](https://github.com/Lindt8/PHITS-Tools)).



## Improving input editing as plaintext, with Sublime Text 

While the Flair tool distributed with FLUKA is good at obscuring the rather antiquated and challenging plaintext syntax of FLUKA inputs and is, comparatively, very approachable, some folks do actually prefer to edit inputs the "old fashioned way" by editing the plaintext files directly (and/or are on macOS, using the [Homebrew package manager](https://brew.sh/), and do not wish to install a new package manager and redundantly install a number of packages just to get Flair working consistently). 

However, owing to the fixed-formatting nature of FLUKA's input syntax, being particularly picky about exact column alignment of input cards, editing FLUKA input in a text editor can be a particularly arduous experience. The [SublimeText_FLUKA_Package](SublimeText_FLUKA_Package) directory contains a package for the text editor Sublime Text that seeks to ease a lot of the tediousness involved with manual editing of the plaintext FLUKA input and make it much easier to draft an input file without entry alignment issues.
