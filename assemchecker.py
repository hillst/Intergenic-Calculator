#!/usr/bin/env python
# encoding: utf-8
'''
assemchecker -- shortdesc



@author:     Steven Hill
            
@copyright:  2013 Donald Danforth Plant Science Center. All rights reserved.
            

@contact:    shill@danforthcenter.org
'''

import sys
import os
from Bio import SeqIO
import Bio
from subprocess import *
import pysam
from optparse import OptionParser

__all__ = []
__version__ = 0.1
__date__ = '2013-08-09'
__updated__ = '2013-08-09'

PROFILE = 0

def main(argv=None):
    '''Command line options.'''
    
    program_name = os.path.basename(sys.argv[0])
    program_version = "v0.1"
    program_build_date = "%s" % __updated__
 
    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    #program_usage = '''usage: spam two eggs''' # optional - will be autogenerated by optparse
    program_longdesc = '''''' # optional - give further explanation about what the program does
    program_license = "Copyright 2013 Steven Hill (Donald Danforth Plant Science Center)                                            \
                Licensed under the Apache License 2.0\nhttp://www.apache.org/licenses/LICENSE-2.0"
 
    if argv is None:
        argv = sys.argv[1:]
        # setup option parser
    parser = OptionParser(version=program_version_string, epilog=program_longdesc, description=program_license)
    parser.add_option("-b", "--bam", dest="bam", help="set input sorted bam file [BAM]", metavar="bam")
    parser.add_option("-r", "--reference", dest="reference", help="reference input file. [FASTA]", metavar="fasta")
    parser.add_option("-a", "--annotation", dest="annotation", help="Annotation file with gene labels. [GFF3]", metavar="gff3")
    parser.add_option("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %default]")
    
    verbose, bam, reference, annotation = None, None, None, None
    # process options
    (opts, args) = parser.parse_args(argv)
    
    if opts.verbose > 0:
        verbose = opts.verbose
        print("verbosity level = %d" % opts.verbose)
    if opts.bam:
        bam = opts.bam.split(",")
    if opts.reference:
        reference = opts.reference
    if opts.annotation:
        annotation = opts.annotation
    if bam is None or reference is None or annotation is None:
        parser.print_usage()
        return -1
    # MAIN BODY #
    AssemChecker(bam, reference, annotation, verbose)
"""
Work is done here

load up our reference, walk through it and calculate the length of each scaffold.

Next build an array of length n, where n is the lenght of the scaffold.
    for each gene in the annotation file contained within that scaffold, mark it's position with a pointer to it's gene structure

Then for each hit in our bam, record it to our gene structure as a hit if the template length is nonzero. 

expects bam to be a list of bamfiles
"""        
def AssemChecker(bam, reference, annotation, verbose):
    #assume sam is already sorted
    sams = []
    for file in bam:
        sams.append(pysam.Samfile(file, "rb"))
    hold = False
    mastergene = []
    prev_scaffold = None
    scaffold = []
    pos = 0
    inpsize = os.stat(annotation)
    inpsize = inpsize.st_size
    with open(annotation, 'r') as ann:
        with open(reference, "r") as ref:
            fasta_parse = SeqIO.parse(ref, "fasta")
            ref_lengths = dict((record.id , len(record.seq)) for record in fasta_parse)
            # python 27 ref_lengths = { record.id : len(record.seq) for record in fasta_parse }
        fasta_parse = None
        for line in ann:
            linearr = line.split()
            if( len(linearr) < 8 ):
                print linearr
                continue
            if "gene" in linearr[2]:
                gene = Gene(line)
                mastergene.append(gene)
                if prev_scaffold != None and gene.scaffold == prev_scaffold:
                    prev_scaffold = gene.scaffold
                if prev_scaffold == None:
                    #initialize
                    prev_scaffold = gene.scaffold
                    scaffold = [None for i in range(ref_lengths[gene.scaffold])]
                if prev_scaffold != gene.scaffold: #new scaffold, process all and reset
                    for sam in sams:
                        process_alignment(scaffold, prev_scaffold , sam)
                    prev_scaffold = gene.scaffold
                    scaffold = [None for i in range(ref_lengths[gene.scaffold])]
                for i in range(gene.start, gene.stop):
                    scaffold[i] = gene
            
            comp = ann.tell()/float(inpsize) * 100
            if i >= comp:
                printPercent(inpsize, comp)
                i += 1

            else:
                continue
            #list current is a array of indexes from the start of the gene to the end, 0-length, containing
            # a gene object if there is a gene there, otherwise NoneType
            
            #process alignments on current scaffold
        total_frags = 0
        for gene in mastergene:
            total_frags += len(gene.hits)
        total_frags = total_frags/1000000.0
        for gene in mastergene:
            print gene.name, len(gene.hits)/(len(gene)/1000.0)/(total_frags)
def printPercent(inputsize, comp):
        print >> sys.stderr,"\r" + ("[" + ("=" * int(comp/10)) +">"+ (" " * (10 - int(comp/10))) + "]"
                           + str(int(comp)) +  "% Complete"),
        sys.stdout.flush()
def process_alignment(scaffold, name , sam):
    while True:
        prev = sam.tell()
        cur = sam.next()
        #print >> sys.stderr , "\r", sam.getrname(cur.tid), current.scaffold,
        if sam.getrname(cur.tid) not in name:
            #repush to pause and wait for scaffold iterator to catch up
            sam.seek(prev)
            break
        try:
            start = cur.pos
            mate = cur.mpos
            length = cur.qlen
            if length < 0:
                tmp = start
                start = mate 
                mate = tmp
            if cur.tlen != 0: 
                #check for off by one
                if(scaffold[start] != None and scaffold[mate] != None):
                    scaffold[start].hits[sam.getrname(cur.tid)] = 1
        except IndexError as e: 
            print "INDEX ERROR", e
            pass

#using this class as a struct
class Gene():
    hits = None
    start = None
    stop = None
    scaffold = None
    linearr = None
    line = None
    strandedness = None
    extra = None
    name = None
    def __init__(self, line):
        linearr = line.split()
        self.hits = {} # this should be a dictionary of hits, where the key is the sequence name
        self.start = int(linearr[3])
        self.stop = int(linearr[4])
        self.scaffold = linearr[0]
        self.linearr = linearr
        self.line = line
        self.strandedness = linearr[6]
        self.extra = linearr[-1]
        self.name = linearr[8].split("=")[1]
    
    def __len__(self):
        return self.stop - self.start
    def __str__(self):
        return "HITS: " + str(len(self.hits)) + " " + self.line
if __name__ == "__main__":
    sys.exit(main())
