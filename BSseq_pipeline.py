# PiGx BSseq Pipeline.
#
# Copyright © 2017, 2018 Bren Osberg <b.osberg@tum.de>
# Copyright © 2017 Alexander Gosdschan <alexander.gosdschan@mdc-berlin.de>
# Copyright © 2017 Katarzyna Wreczycka <katwre@gmail.com>
# Copyright © 2017, 2018 Ricardo Wurmus <ricardo.wurmus@mdc-berlin.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os

#---------------------------     LIST THE OUTPUT DIRECTORIED AND SUBDIRECTORIED TO BE PRODUCED     ------------------------------
WORKDIR = os.getcwd() + "/"                         #--- current work dir (important for rmarkdown)

DIR_scripts   = os.path.join(config['locations']['pkglibexecdir'], 'scripts/')
DIR_templates = os.path.join(config['locations']['output-dir'], 'path_links/report_templates/')
# DIR_xmethed     = 'xx_xmethed/' #--- no longer used

DIR_diffmeth    = '10_differential_methylation/'
DIR_annot       = '09_annotation/'
DIR_seg         = '08_segmentation/'
DIR_methcall    = '07_methyl_calls/'
DIR_sorted      = '06_sorting/'
DIR_deduped     = '05_deduplication/'
DIR_mapped      = '04_mapping/'
DIR_posttrim_QC = '03_posttrimming_QC/'
DIR_trimmed     = '02_trimming/'
DIR_rawqc       = '01_raw_QC/'

DIR_final       = os.path.join(config['locations']['output-dir'], "Final_Report/")


#---------------------------------     DEFINE PATHS AND FILE NAMES:  ----------------------------------

PATHIN          = "path_links/input/"       #--- location of the data files to be imported (script creates symbolic link) 
GENOMEPATH      = "path_links/refGenome/"   #--- where the reference genome being mapped to is stored
VERSION         = config['general']['genome-version']  #--- version of the genome being mapped to.

bismark_cores   = str(config['tools']['bismark']['cores'])

def prog(name):
    config['tools'][name]['executable']

def generateReport(input, output, params, log, reportSubDir):
    dumps = json.dumps(dict(params.items()),sort_keys=True,
                       separators=(",",":"), ensure_ascii=True)

    cmd =   "{prog('Rscript')} {DIR_scripts}/report_functions.R"
    cmd +=  " --reportFile={input.template}"
    cmd +=  " --outFile={output.report}"
    cmd +=  " --finalReportDir=" + os.path.join(DIR_final,reportSubDir)
    cmd +=  " --report.params={dumps:q}"
    cmd +=  " --logFile={log}"
    shell(cmd, dumps)

# include function definitions and extra rules
include   : os.path.join(config['locations']['pkglibexecdir'], 'scripts/func_defs.py')

#---------------------------     LIST THE OUTPUT FILES TO BE PRODUCED     ------------------------------

# Below is a mapping of rule names to the expected output files they
# produce.  The desired output files are specified in
# "OUTPUT_FILES".  A different set of output files can be
# selected to run fewer rules.

targets = {
    # rule to print all rule descriptions
    'help': {
        'description': "Print all rules and their descriptions.",
        'files': []
    },

    # These are expensive one-time rules to prepare the genome.
    'genome-prep-CT': {
        'description': "C-to-T convert reference genome into Bisulfite analogue.",
        'files': GENOMEPATH+"Bisulfite_Genome/CT_conversion/genome_mfa.CT_conversion.fa"
    },

    'genome-prep-GA': {
        'description': "G-to-A convert reference genome into Bisulfite analogue.",
        'files': GENOMEPATH+"Bisulfite_Genome/GA_conversion/genome_mfa.GA_conversion.fa"
    },

    '01-raw-qc': {
        'description': "Perform raw quality control.",
        'files': files_for_sample(list_files_rawQC)
    },

    # This rule is always executed, as trimming is a prerequisite for
    # subsequent rules
    '02-trimgalore': {
        'description': "Trim the reads.",
        'files': files_for_sample(list_files_TG)
    },

    # fastQC output files are not needed downstream and need to be
    # called explicitly.
    '03-posttrim-qc': {
        'description': "Perform quality control after trimming.",
        'files': files_for_sample(list_files_posttrim_QC)
    },

    '04-mapping': {
        'description': "Align and map reads with Bismark.",
        'files': files_for_sample(list_files_bismark)
    },

    '05-deduplication': {
        'description': "Deduplicate bam files.",
        'files': files_for_sample(list_files_dedupe)
    },

    '06-sorting': {
        'description': "Sort bam files.",
        'files': files_for_sample(list_files_sortbam)
    },

     # TODO: had to add this part to call bam_methCall for diff meth rule
    'bam-processing': {
        'description': "Process bam files.",
        'files': [
            expand (bam_processing(DIR_methcall,
                                   config["SAMPLES"][sample]["files"],
                                   sample))
            for sample in config["SAMPLES"]
        ]
    },

    'diffmeth': {
        'description': "Perform differential methylation calling.",
        'files': [ DIR_diffmeth+"_".join(x)+".sorted_diffmeth.nb.html" for x in config["DIFF_METH"]]
    },
		            
    'annotation': {
        'description': "Annotate differential methylation cytosines.",
        'files': [ DIR_annot+"_".join(x)+".sorted_"+config['general']['genome-version']+"_annotation.diff.meth.nb.html" for x in config["DIFF_METH"]]
    },

    'final-report': {
        'description': "Produce a comprehensive report.  This is the default target.",
        'files': [
            expand (Final(DIR_final,
                          config["SAMPLES"][sample]["files"],
                          VERSION,
                          config["SAMPLES"][sample]["SampleID"]))
            for sample in config["SAMPLES"]
        ]
    }
}

# Selected output files from the above set.
selected_targets = [ config['execution']['target'] ]
OUTPUT_FILES = [targets[name]['files'] for name in selected_targets]

#--- NICE gauges the computational burden, ranging from -19 to +19.
#--- The more "nice" you are, the more you allow other processes to jump ahead of you
#--- (like in traffic). Generally set to maximally nice=19 to avoid interference with other users.
def nice(cmd):
    return "nice -" + str(config['execution']['nice']) + " " + cmd

#--- In case you want to debug the code with interactive commands:
# import IPython;
# IPython.embed()
# print("Executing job to produce the following files: ")
# print("OUTPUT_FILES=")
# for x in OUTPUT_FILES: print( x)
#-------

# ==============================================================================================================
#
#                                         BEGIN RULES    
#
# rules are separated by "==" bars into pairs for paired-end and single-end (subdivided by smaller "--" dividers)
# ===============================================================================================================

rule all:
    input:
        OUTPUT_FILES
    run:
        # Describe all targets if "help" was requested.
        if config['execution']['target'] == 'help':
            for key in sorted(targets.keys()):
                print('{}:\n  {}'.format(key, targets[key]['description']))

# ==========================================================================================
# sort the bam file:

rule sortbam_se:
    input:
        DIR_deduped+"{sample}_se_bt2.deduped.bam"
    output:
        DIR_sorted+"{sample}_se_bt2.deduped.sorted.bam"
    message: fmt("Sorting bam file {input}")
    shell:
        nice("{prog('samtools')} sort {input} -o {output}")
#-----------------------
rule sortbam_pe:
    input:
        DIR_deduped+"{sample}_1_val_1_bt2.deduped.bam"
    output:
        DIR_sorted+"{sample}_1_val_1_bt2.deduped.sorted.bam"
    message: fmt("Sorting bam file {input}")
    shell:
        nice("{prog('samtools')} sort {input} -o {output}")

# ==========================================================================================
# deduplicate the bam file:

rule deduplication_se:
    input:
        DIR_mapped+"{sample}_trimmed_bismark_bt2.bam"
    output:
        DIR_deduped+"{sample}_se_bt2.deduped.bam"
    params:
        bam="--bam ",
        sampath="--samtools_path "+prog('samtools')
    log:
        DIR_deduped+"{sample}_deduplication.log"
    message: fmt("Deduplicating single-end aligned reads from {input}")
    shell:
        nice("{prog('samtools')} rmdup {input}  {output} > {log} 2>&1 ")
#-----------------------
rule deduplication_pe:
    input:
        DIR_mapped+"{sample}_1_val_1_bismark_bt2_pe.bam"
    output:
        DIR_deduped+"{sample}_1_val_1_bt2.deduped.bam"
    log:
        DIR_deduped+"{sample}_deduplication.log"
    message: fmt("Deduplicating paired-end aligned reads from {input}")
    shell:
        nice("{prog('samtools')} fixmate {input}  {output} > {log} 2>&1 ")

# ==========================================================================================
# align and map:
 
rule bismark_se:
    input:
        refconvert_CT = GENOMEPATH+"Bisulfite_Genome/CT_conversion/genome_mfa.CT_conversion.fa",
	refconvert_GA = GENOMEPATH+"Bisulfite_Genome/GA_conversion/genome_mfa.GA_conversion.fa",
        fqfile = DIR_trimmed+"{sample}_trimmed.fq.gz",
        qc     = DIR_posttrim_QC+"{sample}_trimmed_fastqc.html"
    output:
        DIR_mapped+"{sample}_trimmed_bismark_bt2.bam",
        DIR_mapped+"{sample}_trimmed_bismark_bt2_SE_report.txt"
    params:
        bismark_args = config['tools']['bismark']['args'],
        genomeFolder = "--genome_folder " + GENOMEPATH,
        outdir = "--output_dir  "+DIR_mapped,
        nucCov = "--nucleotide_coverage",
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(prog('bowtie2')) ,
        useBowtie2  = "--bowtie2 ",
        samtools    = "--samtools_path "+ os.path.dirname(prog('samtools')),
        tempdir     = "--temp_dir "+DIR_mapped
    log:
        DIR_mapped+"{sample}_bismark_se_mapping.log"
    message: fmt("Mapping single-end reads to genome {VERSION}")
    shell:
        nice("{prog('bismark')} {params} --multicore "+bismark_cores+" {input.fqfile} > {log}  2>&1 ")

#-----------------------

rule bismark_pe:
    input:
        refconvert_CT = GENOMEPATH+"Bisulfite_Genome/CT_conversion/genome_mfa.CT_conversion.fa",
	refconvert_GA = GENOMEPATH+"Bisulfite_Genome/GA_conversion/genome_mfa.GA_conversion.fa",
        fin1 = DIR_trimmed+"{sample}_1_val_1.fq.gz",
        fin2 = DIR_trimmed+"{sample}_2_val_2.fq.gz",
        qc   = [ DIR_posttrim_QC+"{sample}_1_val_1_fastqc.html",
                 DIR_posttrim_QC+"{sample}_2_val_2_fastqc.html"]
    output:
        DIR_mapped+"{sample}_1_val_1_bismark_bt2_pe.bam",
        DIR_mapped+"{sample}_1_val_1_bismark_bt2_PE_report.txt"
    params:
        bismark_args = config['tools']['bismark']['args'],
        genomeFolder = "--genome_folder " + GENOMEPATH,
        outdir = "--output_dir  "+DIR_mapped,
        nucCov = "--nucleotide_coverage",
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(prog('bowtie2')) ,
        useBowtie2  = "--bowtie2 ",
        samtools    = "--samtools_path "+ os.path.dirname(prog('samtools')),
        tempdir     = "--temp_dir "+DIR_mapped
    log:
        DIR_mapped+"{sample}_bismark_pe_mapping.log"
    message: fmt("Mapping paired-end reads to genome {VERSION}.")
    shell:
        nice("{prog('bismark')} {params} --multicore "+bismark_cores+" -1 {input.fin1} -2 {input.fin2} > {log} 2>&1 ")


# ==========================================================================================
# generate reference genome:

rule bismark_genome_preparation:
    input:
        GENOMEPATH
    output:
        GENOMEPATH+"Bisulfite_Genome/CT_conversion/genome_mfa.CT_conversion.fa",
        GENOMEPATH+"Bisulfite_Genome/GA_conversion/genome_mfa.GA_conversion.fa"
    params:
        bismark_genome_preparation_args = config['tools']['bismark-genome-preparation']['args'],
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(prog('bowtie2')) ,
        useBowtie2 = "--bowtie2 ",
        verbose = "--verbose "
    log:
        'bismark_genome_preparation_'+VERSION+'.log'
    message: fmt("Converting {VERSION} Genome into Bisulfite analogue")
    shell:
        nice("{prog('bismark-genome-preparation')} {params} {input} > {log} 2>&1 ")

# ==========================================================================================
# post-trimming quality control

rule fastqc_after_trimming_se:
    input:
        DIR_trimmed+"{sample}_trimmed.fq.gz",
    output:
    	DIR_posttrim_QC+"{sample}_trimmed_fastqc.html",
    	DIR_posttrim_QC+"{sample}_trimmed_fastqc.zip"
    params:
        fastqc_args = config['tools']['fastqc']['args'],
        outdir = "--outdir "+DIR_posttrim_QC
    log:
   	    DIR_posttrim_QC+"{sample}_trimmed_fastqc.log"
    message: fmt("Quality checking trimmmed single-end data from {input}")
    shell:
        nice("{prog('fastqc')} {params.outdir} {input} > {log} 2>&1 ")
#--------
rule fastqc_after_trimming_pe:
    input:
        DIR_trimmed+"{sample}_1_val_1.fq.gz",
        DIR_trimmed+"{sample}_2_val_2.fq.gz"
    output:
    	DIR_posttrim_QC+"{sample}_1_val_1_fastqc.html",
    	DIR_posttrim_QC+"{sample}_1_val_1_fastqc.zip",
    	DIR_posttrim_QC+"{sample}_2_val_2_fastqc.zip",
        DIR_posttrim_QC+"{sample}_2_val_2_fastqc.html"
    params:
        fastqc_args = config['tools']['fastqc']['args'],
        outdir = "--outdir "+DIR_posttrim_QC
    log:
   	    DIR_posttrim_QC+"{sample}_trimmed_fastqc.log"
    message: fmt("Quality checking trimmmed paired-end data from {input}")
    shell:
        nice("{prog('fastqc')} {params.outdir} {input} > {log} 2>&1 ")

# ==========================================================================================
# trim the reads

rule trimgalore_se:
    input:
       qc   = DIR_rawqc+"{sample}_fastqc.html",
       file = PATHIN+"{sample}.fq.gz"
    output:
       DIR_trimmed+"{sample}_trimmed.fq.gz" #---- this ALWAYS outputs .fq.qz format.
    params:
       extra          = config['tools']['trim-galore']['args'],
       outdir = "--output_dir "+DIR_trimmed,
       phred = "--phred33",
       gz = "--gzip",
       cutadapt = "--path_to_cutadapt "+prog('cutadapt'),
    log:
       DIR_trimmed+"{sample}.trimgalore.log"
    message: fmt("Trimming raw single-end read data from {input}")
    shell:
       nice("{prog('trim-galore')} {params} {input.file} > {log} 2>&1 ")

#-----------------------
rule trimgalore_pe:
    input:
        qc    = [ DIR_rawqc+"{sample}_1_fastqc.html",
                  DIR_rawqc+"{sample}_2_fastqc.html"],
        files = [ PATHIN+"{sample}_1.fq.gz",
                  PATHIN+"{sample}_2.fq.gz"]
    output:
        DIR_trimmed+"{sample}_1_val_1.fq.gz", #---- this ALWAYS outputs .fq.qz format.
        DIR_trimmed+"{sample}_2_val_2.fq.gz",
    params:
        extra          = config['tools']['trim-galore']['args'],
        outdir         = "--output_dir "+DIR_trimmed,
        phred          = "--phred33",
        gz             = "--gzip",
        cutadapt       = "--path_to_cutadapt "+prog('cutadapt'),
        paired         = "--paired"
    log:
        DIR_trimmed+"{sample}.trimgalore.log"
    message:
        fmt("Trimming raw paired-end read data from {input}")
    shell:
        nice("{prog('trim-galore')} {params} {input.files} > {log} 2>&1 ")

# ==========================================================================================
# raw quality control

rule fastqc_raw: #----only need one: covers BOTH pe and se cases.
    input:
        PATHIN+"{sample}.fq.gz"
    output:
        DIR_rawqc+"{sample}_fastqc.html",
        DIR_rawqc+"{sample}_fastqc.zip"
    params:
        fastqc_args = config['tools']['fastqc']['args'],
        outdir = "--outdir "+ DIR_rawqc     # usually pass params as strings instead of wildcards.
    log:
        DIR_rawqc+"{sample}_fastqc.log"
    message: fmt("Quality checking raw read data from {input}")
    shell:
        nice("{prog('fastqc')} {params}  {input} > {log} 2>&1 ")



# Rules to be applied after mapping reads with Bismark

## Bam processing
rule bam_methCall:
    input:
        template    = os.path.join(DIR_templates,"methCall.report.Rmd"),
        bamfile     = os.path.join(DIR_sorted,"{prefix}.sorted.bam")
    output:
        report      = os.path.join(DIR_methcall,"{prefix}.sorted_meth_calls.nb.html"),
        rdsfile     = os.path.join(DIR_methcall,"{prefix}.sorted_methylRaw.RDS"),
        callFile    = os.path.join(DIR_methcall,"{prefix}.sorted_CpG.txt")
    params:
        ## absolute path to bamfiles
        inBam       = os.path.join(WORKDIR,DIR_sorted,"{prefix}.sorted.bam"),
        assembly    = config['general']['genome-version'],
        mincov      = int(config['general']['methylation-calling']['minimum-coverage']),
        minqual     = int(config['general']['methylation-calling']['minimum-quality']),
        ## absolute path to output folder in working dir
        rds         = os.path.join(WORKDIR,DIR_methcall,"{prefix}.sorted_methylRaw.RDS")
    log:
        os.path.join(DIR_methcall,"{prefix}.sorted_meth_calls.log")
    message:
        "Processing bam file:\n"
        "   input     : {input.bamfile}" + "\n"
        "Generating:"+ "\n" 
        "   report    : {output.report}" + "\n" 
        "   rds       : {output.rdsfile}" + "\n" 
        "   methCalls : {output.callFile}"
    run:
        generateReport(input, output, params, log, wildcards.prefix)

#----------------------------------- START METH SEGMENTATION


## Segmentation
rule methseg:
    ## paths inside input and output should be relative
    input:
        template    = os.path.join(DIR_templates,"methseg.report.Rmd"),
        rdsfile     = os.path.join(DIR_methcall,"{prefix}.sorted_methylRaw.RDS")
    output: 
        report      = os.path.join(DIR_seg,"{prefix}.sorted_meth_segments.nb.html"),
        grfile      = os.path.join(DIR_seg,"{prefix}.sorted_meth_segments_gr.RDS"),
        bedfile     = os.path.join(DIR_seg,"{prefix}.sorted_meth_segments.bed"),
    params:
        rds         = os.path.join(WORKDIR,DIR_methcall,"{prefix}.sorted_methylRaw.RDS"),
        grds        = os.path.join(WORKDIR,DIR_seg,"{prefix}.sorted_meth_segments_gr.RDS"),
        outBed      = os.path.join(WORKDIR,DIR_seg,"{prefix}.sorted_meth_segments.bed")
    log:
        os.path.join(DIR_seg,"{prefix}.sorted_meth_segments.log")
    message:
        "Segmentation of sample file:\n"
        "   input     : {input.rdsfile}" + "\n" 
        "Generating:"+ "\n"
        "   report    : {output.report}" + "\n"
        "   grfile    : {output.grfile} " +"\n"
        "   bedfile   : {output.bedfile}" +"\n"
    run:
        generateReport(input, output, params, log, wildcards.prefix)


## Aquisition of gene features
rule fetch_refGene:
    output: refgenes = os.path.join(DIR_annot,"refseq.genes.{assembly}.bed")
    params:
        assembly = "{assembly}"
    log:
        os.path.join(DIR_annot,"fetch_refseq.genes.{assembly}.log")
    message:
        "Fetching RefSeq genes for Genome assembly: {wildcards.assembly}"
    shell:
        "{prog('Rscript')} {DIR_scripts}/fetch_refGene.R {log} {output.refgenes} {params.assembly}"


## Annotation with gene features
rule methseg_annotation:
    input:
        template    = os.path.join(DIR_templates,"annotation.report.Rmd"),
        bedfile     = os.path.join(DIR_seg,"{prefix}.sorted_meth_segments.bed"),
        refgenes    = os.path.join(DIR_annot,"refseq.genes.{assembly}.bed")
    output:
        report      = os.path.join(DIR_annot,"{prefix}.sorted_{assembly}_annotation.nb.html"),
    params:
        inBed       = os.path.join(WORKDIR,DIR_seg,"{prefix}.sorted_meth_segments.bed"),
        assembly    = "{assembly}",# expand(config["reference"]),
        refseqfile  = os.path.join(WORKDIR,DIR_annot,"refseq.genes.{assembly}.bed")
    log:
        os.path.join(DIR_annot,"{prefix}.sorted_{assembly}_annotation.log")
    message:
        "Annotation of Segments:\n"
        "   input     : {input.bedfile}" + "\n"
        "Generating:" + "\n"
        "   report    : {output.report}"
    run:
        generateReport(input, output, params, log, wildcards.prefix)

#----------------------------------- END METH SEGMENTATION
#----------------------------------- START DIFF METH

SAMPLE_IDS = list(config["SAMPLES"].keys())
SAMPLE_TREATMENTS = [config["SAMPLES"][s]["Treatment"] for s in SAMPLE_IDS]


def get_sampleids_from_treatment(treatment):
  treatments = treatment.split("_")
  sampleids_list = []
  for t in treatments:
    sampleids = [SAMPLE_IDS[i] for i, x in enumerate(SAMPLE_TREATMENTS) if x == t]
    sampleids_list.append(sampleids)
  
  sampleids_list = list(sum(sampleids_list, []))
  
  return(sampleids_list)


# For only CpG context
def diffmeth_input_function(wc):

  treatments = wc.treatment
  sampleids = get_sampleids_from_treatment(treatments)
  
  inputfiles = []
  for sampleid in sampleids:
    fqname = config["SAMPLES"][sampleid]['fastq_name']
    if len(fqname)==1:
      inputfile=[os.path.join(DIR_methcall,sampleid+"_se_bt2.deduped.sorted_CpG.txt")]
    elif len(fqname)==2:
      inputfile=[os.path.join(DIR_methcall,sampleid+"_1_val_1_bt2.deduped.sorted_CpG.txt")]
    inputfiles.append(inputfile)
  
  inputfiles = list(sum(inputfiles, []))
  return(inputfiles)


## Differential methylation
rule diffmeth:
    ## paths inside input and output should be relative
    input:  
        template    = os.path.join(DIR_templates,"diffmeth.report.Rmd"),
        inputfiles  = diffmeth_input_function
    output: 
        report      = os.path.join(DIR_diffmeth,"{treatment}.sorted_diffmeth.nb.html"),
        methylDiff_file  = os.path.join(DIR_diffmeth,"{treatment}.sorted_diffmeth.RDS"),
        bedfile     = os.path.join(DIR_diffmeth,"{treatment}.sorted_diffmeth.bed"),
    params:
        workdir     = WORKDIR,
        inputfiles  = diffmeth_input_function,
        sampleids   = lambda wc: get_sampleids_from_treatment(wc.treatment),
        methylDiff_file      = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmeth.RDS"),
        methylDiff_hyper_file  = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmethhyper.RDS"),
        methylDiff_hypo_file   = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmethhypo.RDS"),
        outBed      = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmeth.bed"),
        assembly    = config['general']['genome-version'],
        treatment   = lambda wc: [config["SAMPLES"][sampleid]['Treatment'] for sampleid in get_sampleids_from_treatment(wc.treatment)],
        mincov      = int(config['general']['methylation-calling']['minimum-coverage']),
        context     = "CpG",
        cores       = int(config['general']['differential-methylation']['cores'])
    log:
        os.path.join(DIR_diffmeth+"{treatment}.sorted_diffmeth.log")
    run:
        generateReport(input, output, params, log, wildcards.treatment)


## Annotation with gene features
rule annotation_diffmeth:
    input:  
        template    = os.path.join(DIR_templates,"annotation.report.diff.meth.Rmd"),
        bedfile     = os.path.join(DIR_diffmeth,"{treatment}.sorted_diffmeth.bed"),
        refgenes    = os.path.join(DIR_annot,"refseq.genes.{assembly}.bed")
    output: 
        report      = os.path.join(DIR_annot,"{treatment}.sorted_{assembly}_annotation.diff.meth.nb.html"),
    params:
        inBed       = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmeth.bed"),
        assembly    = config['general']['genome-version'],
        refseqfile  = os.path.join(WORKDIR,DIR_annot,"refseq.genes.{assembly}.bed"),
        methylDiff_file  = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmeth.RDS"),
        methylDiff_hyper_file = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmethhyper.RDS"),
        methylDiff_hypo_file  = os.path.join(WORKDIR,DIR_diffmeth,"{treatment}.sorted_diffmethhypo.RDS"),
        ideoDMC_script = os.path.join(DIR_scripts,"ideoDMC.R")
    log:
        os.path.join(DIR_annot,"{treatment}.sorted_{assembly}_annotation.diff.meth.log")
    run:
        generateReport(input, output, params, log, wildcards.treatment+"."+wildcards.assembly)

#----------------------------------- END DIFF METH
   

### note that Final report can only be generated 
### if one of the intermediate has been genereted,
### so make sure that at least one has been run already
### right now ensured with 'rules.methseg_annotation.output' as input
### 


def get_fastq_name(full_name):
    # single end
    find_se_inx=full_name.find('_se_bt2')
    # paired-end
    find_pe_inx=full_name.find('_1_val_1_bt2')
    
    if(find_se_inx>=0):
      output=full_name[:find_se_inx]
    elif(find_pe_inx>=0):
     output=full_name[:find_pe_inx]
    else:
     print("Sth went wrong")
    
    return(output)


SAMPLE_TREATMENTS_DICT = dict(zip(SAMPLE_IDS, SAMPLE_TREATMENTS))
DIFF_METH_TREATMENT_PAIRS = config['DIFF_METH']

def diff_meth_input(wc):
  sample = wc.prefix
  sampleid = get_fastq_name(sample)
  treatment_of_sampleid = SAMPLE_TREATMENTS_DICT[ sampleid ]
  
  mylist = []
  for x in DIFF_METH_TREATMENT_PAIRS:
    if treatment_of_sampleid in x:
      name_of_dir = x[0]+"_"+x[1]+".sorted_"+wc.assembly+"_annotation.diff.meth.nb.html"
      mylist.append(DIR_annot + name_of_dir)
  return(mylist)


rule integrateFinalReport:
    input:
       diffmeth = diff_meth_input
    output:
       touch(DIR_final + "{prefix}_{assembly}_integrateDiffMeth2FinalReport.txt")
    log:
       DIR_final + "{prefix}_{assembly}_integrateFinalReport.log"
    params:
       diffmeth = lambda wildcards: ' '.join(map('{}'.format, diff_meth_input(wildcards)))
    shell:
      "{prog('Rscript')} {DIR_scripts}/integrate2finalreport.R {wildcards.prefix} {wildcards.assembly} {DIR_final} {params.diffmeth}"


## Final Report
rule final_report:
    input:  
        rules.methseg_annotation.output,
        rules.integrateFinalReport.output,
        index       = os.path.join(DIR_templates,"index.Rmd"),   
        references  = os.path.join(DIR_templates,"references.Rmd"),
        sessioninfo = os.path.join(DIR_templates,"sessioninfo.Rmd")
    output: 
        finalreport = os.path.join(DIR_final, "{prefix}.sorted_{assembly}_final.nb.html"),
    params:
        finalreportdir = os.path.join(DIR_final, "{prefix}/")
    log:
        os.path.join(DIR_final,"{prefix}.sorted_{assembly}_final.log")
    message:
        "Compiling Final Report:\n"
        "   report    : {output.finalreport}"
        
    run:
        cmd  =  "{prog('Rscript')} {DIR_scripts}/multireport_functions.R"
        cmd +=  " --index={input.index}"
        cmd +=  " --finalOutput={output.finalreport}"
        cmd +=  " --finalReportDir={params.finalreportdir}"
        cmd +=  " --references={input.references}"
        cmd +=  " --sessioninfo={input.sessioninfo}"
        cmd +=  " --logFile={log}"
        
        shell(cmd)

