# About

This is a script that extracts annotations (highlights, comments, etc.) 
from a PDF file, and formats them as markdown text. It is intended for 
use in reviewing conference papers.

At present, the following annotations are supported:

 * Highlights without an attached comment are output first, as
   "highlights" with just the highlighted text included. Note that
   these are not typically suitable for use in a review, since they're
   unlikely to have any meaning to the recipient; they are just meant
   to serve as a reminder to the reviewer.

 * Highlights with an attached comment, and text annotations (not
   attached to any particular text/highlight) are output next, as
   "detailed comments". Typically most comments on a reviewed paper
   are of this form.

 * Underline, strikeout, and squiggly underline annotations are output
   last, as "Nits", with or without an attached comment. The intention
   of this is to easily separate formatting or grammatical corrections
   from more substantial comments about the content of the document.

For each annotation, the page number is given, along with the
associated (highlighted/underlined) text, if any. Additionally, if the
documents includes outlines (aka bookmarks) such as those generated by
the hyperref package, those are also used to identify to which section
in the document the annotation refers.


# Usage

The intended usage of this tool is as a reviewing aid. I typically
review a paper directly in my PDF reader, annotating it liberally as I
read it (and using squiggly/underline for minor nits). When I've
finished reading the paper, I use this script to convert the
annotations to plain text, which I paste into the appropriate section
of the review form and then edit accordingly to add a high-level
review, correct formatting, fix typos, update or remove inaccurate
comments, etc.

See `pdfannots.py --help` for options and invocation.


# Limitations

At present the script has a number of limitations:

 * It assumes left-to-right top-to-bottom page layout

 * pdfminer (the underlying PDF parser) sometimes fails to extract text from PDF
   files when other converters (e.g. pdftotext) do just fine; this results in
   annotations with some or all text missing (in which case you'll see `XXX:
   missing text`)

 * The output from strikeout annotations is not very meaningful


# Dependencies

 * Python 3
 * [pdfminer.six package](https://github.com/pdfminer/pdfminer.six) and its dependencies; e.g.: `pip3 install pdfminer.six`

# FAQ

## I'd like to change how the output is formatted.

Some minor changes (e.g.: word wrap, skipping sections) can be accomplished
via command-line arguments. See `pdfannots.py --help`.

All of the output comes from the `PrettyPrinter` class; more elaborate changes
can probably be accomplished there.

## I think I got a review generated by this tool...

I hope that it was a constructive review, and that the annotations
helped the reviewer give you more detailed feedback so you can improve
your paper. This is, after all, just a tool, and it should not be an
excuse for reviewer sloppiness. Note that I am not the only user of
this script.


# Author

Andrew Baumann
