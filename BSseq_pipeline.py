#!/usr/bin/env python3.5

#============================================================================================================
# SNAKEMAKE FILE WRITTEN BY THE AKALIN GROUP AT MDC, BERLIN, 2017
# Alexander Gosdschan, Katarzyna Wreczycka, Bren Osberg
# To process bisulfite sequencing data from raw fastq files to performing integrated bioinformatics analysis.

# SUBMIT THIS JOB INTERACTIVELY WITH:
# $nohup  snakemake -s [this filename] --jobs [# of jobs to submit] > [logfilename] &
# You can also add the following options for cluster submission: --cluster "qsub -V -l h_vmem={params.mem} -pe smp {params.threads} -l h_rt=36:00:00" &

# import IPython;
# IPython.embed()
 
#============================================================================================================

#------ set config file, include function definitions, and set os:
import os
include   : "./scripts/func_defs.py"

#---------------------------     LIST THE OUTPUT DIRECTORIED AND SUBDIRECTORIED TO BE PRODUCED     ------------------------------

# Check if given directories exist, if they dont create them:
for x in [config["PATHIN"], config["PATHOUT"], config["LOG"]]:
  if not os.path.exists(x):
    os.makedirs(x)

DIR_sorted=config["PATHOUT"]+'06_sorted/'
DIR_mapped=config["PATHOUT"]+'04_mapped/'
DIR_deduped=config["PATHOUT"]+'05_deduped/'
DIR_posttrim_QC=config["PATHOUT"]+'03_posttrim_QC/'
DIR_trimmed=config["PATHOUT"]+'02_trimmed/'
DIR_rawqc=config["PATHOUT"]+'01_rawqc/'

for x in [DIR_rawqc, DIR_trimmed, DIR_posttrim_QC, DIR_mapped, DIR_deduped, DIR_sorted]:
  if not os.path.exists(x):
    os.makedirs(x)


#---------------------------------     DEFINE PATHS AND FILE NAMES:  ----------------------------------

PATHIN          = config["PATHIN"]         #--- location of the data files to be imported
PATHOUT         = config["PATHOUT"]        #--- where to send the output
GTOOLBOX        = config["GTOOLBOX"]       #--- where the programs are stored to carry out the necessary operations
GENOMEPATH      = config["GENOMEPATH"]     #--- where the reference genome being mapped to is stored

LOGS            = config["LOG"]           #--- subfolder name for the logs of some programs

VERSION         = config["GENOME_VERSION"]  #--- version of the genome being mapped to.

CHROM_INFO      = config["CHROM_INFO"]     #--- details of the reference genome (length, etc.) haploid chroms have been removed.
NUMTHREADS      = config["NUMTHREADS"]

INEXT = config["INEXT"]
NICE=str(19)
RCODE = config["RCODE"]

#-------------------------------      DEFINE PROGRAMS TO BE EXECUTED: ---------------------------------

FASTQC                         =  GTOOLBOX+config["PROGS"]["FASTQC"]            #--- self-explanatory program names.
TRIMGALORE                     =  GTOOLBOX+config["PROGS"]["TRIMGALORE"]
CUTADAPT                       =  GTOOLBOX+config["PROGS"]["CUTADAPT"]
BISMARK_GENOME_PREPARATION     =  GTOOLBOX+config["PROGS"]["BISMARK_GENOME_PREPARATION"]
BISMARK                        =  GTOOLBOX+config["PROGS"]["BISMARK"]
BOWTIE2                        =  GTOOLBOX+config["PROGS"]["BOWTIE2"]
DEDUPLICATE_BISMARK            =  GTOOLBOX+config["PROGS"]["DEDUPLICATE_BISMARK"]
BISMARK_METHYLATION_EXTRACTOR  =  GTOOLBOX+config["PROGS"]["BISMARK_METHYLATION_EXTRACTOR"]
BISMARK2REPORT                 =  GTOOLBOX+config["PROGS"]["BISMARK2REPORT"]

SAMTOOLS                       =  GTOOLBOX+config["PROGS"]["SAMTOOLS"]


#---------------------------     LIST THE OUTPUT FILES TO BE PRODUCED     ------------------------------

# --- Below is the list of expected output files. They are enumerated by their sequence in the rules of the processing pipeline
# --- the process can be terminated earlier by expressing (i.e. uncommenting) only the [expand] commands corresponding to the 
# --- last rule that you wish to have executed.


OUTPUT_FILES = [
                #               ======  rule 01 raw QC    =========
                [ expand (list_files(DIR_rawqc, config["SAMPLES"][sampleID]["fastq_name"], "_fastqc.html")  ) for sampleID in config["SAMPLES"]  ],
                [ expand (list_files(PATHOUT+"01_rawqc/", config["SAMPLES"][sampleID]["fastq_name"], "_fastqc.zip" )  ) for sampleID in config["SAMPLES"]  ],

                #----RULE 2 IS ALWAYS EXECUTED, TRIMMING IS A PREREQUISITE FOR SUBSEQUENT RULES ----
                
                #               ======  rule 03 posttrim_QC_ ======
                [ expand ( list_files_posttrim_QC(DIR_posttrim_QC, config["SAMPLES"][sampleID]["fastq_name"],".html")  ) for sampleID in config["SAMPLES"]  ],
                [ expand ( list_files_posttrim_QC(DIR_posttrim_QC, config["SAMPLES"][sampleID]["fastq_name"],".zip")  ) for sampleID in config["SAMPLES"]  ],

                #--- fastQC output files are not needed downstream and need to be called explicitly.

                
                #-----  here is a list of intermediary files to be uncommented back into execution if you want to stop part-way along the process -----------------
                #               ====rule 02 trimgalore ======
                [ expand ( list_files_TG( DIR_trimmed, config["SAMPLES"][sampleID]["fastq_name"] )  ) for sampleID in config["SAMPLES"]  ],
                #               ====rule 04 Mapping ======
                [ expand ( list_files_bismark(DIR_mapped, config["SAMPLES"][sampleID]["fastq_name"] )  ) for sampleID in config["SAMPLES"]  ],
              
                #               ====formerly rule 05 Deduplication ======
                [ expand ( list_files_dedupe(DIR_deduped, config["SAMPLES"][sampleID]["fastq_name"] )  ) for sampleID in config["SAMPLES"]  ],                                

                #               ====rule 06 sorting ======
                [ expand ( list_files_sortbam(DIR_sorted, config["SAMPLES"][sampleID]["fastq_name"] )  ) for sampleID in config["SAMPLES"]  ],
                
                # ==================  FINAL REPORT =========================
                # @@@! This needs to be editted once we determine what final reports we want to export!
		# [ expand (PATHOUT+config["SAMPLES"][sampleID]["fastq_name"][0]+SEPEstr(config["SAMPLES"][sampleID]["fastq_name"] )+"_report.html"  ) for sampleID in config["SAMPLES"]  ],
                
]


# =======================================================================================================
#
#                                         BEGIN RULES    
#
# =======================================================================================================

rule all:
    input:
        OUTPUT_FILES

# --------------------------------------------------------------------------------
# rule clean:
#    shell: "if [ -d {PATHOUT} ]; then rm -r {PATHOUT}; fi"
# ==========================================================================================


rule sortbam_se:
    input:
        DIR_deduped+"{sample}_se_bt2.deduped.bam"
    output:
        DIR_sorted+"{sample}_se_bt2.deduped.sorted.bam"
    shell:
        "nice -"+str(NICE)+" {SAMTOOLS} sort {input} -o {output}"

#-------- TWO SORTING STEPS ARE REQUIRED IN PAIRED END (see bismark deduplication doc) -----
rule sortbam_pe:
    input:
        DIR_deduped+"{sample}"+RCODE+"1_val_1_bt2.deduped.bam"
    output:
        DIR_sorted+"{sample}"+RCODE+"1_val_1_bt2.deduped.sorted.bam"
    shell:
        "nice -"+str(NICE)+" {SAMTOOLS} sort {input} -o {output}"

# ==========================================================================================

rule bismark_se_deduplication:
    input:
        DIR_mapped+"{sample}_trimmed_bismark_bt2.bam"
    output:
        DIR_deduped+"{sample}_se_bt2.deduped.bam"
    params:
        bam="--bam ",
        sampath="--samtools_path "+SAMTOOLS
    log:
        DIR_deduped+"{sample}_deduplication.log"
    message: """-----------   Deduplicating single-end read alignments ---------------------- """
    shell:
        "nice -"+str(NICE)+" {SAMTOOLS} rmdup {input}  {output} 2> {log}"
# #--------
rule bismark_pe_deduplication:
    input:
        DIR_mapped+"{sample}"+RCODE+"1_val_1_bismark_bt2_pe.bam"
    output:
        DIR_deduped+"{sample}"+RCODE+"1_val_1_bt2.deduped.bam"
    log:
        DIR_deduped+"{sample}_deduplication.log"
    message: """-----------   Deduplicating paired-end read alignments ---------------------- """
    shell:
        "nice -"+str(NICE)+" {SAMTOOLS} rmdup {input}  {output} 2> {log}"
# ==========================================================================================
# Align and map:
# 
rule bismark_se:
    input:
       DIR_trimmed+"{sample}_trimmed.fq.gz"
    output:
        DIR_mapped+"{sample}_trimmed_bismark_bt2.bam",
        DIR_mapped+"{sample}_trimmed_bismark_bt2_SE_report.txt"
    threads: 2
    params:
        genomeFolder = "--genome_folder " + GENOMEPATH,
        outdir = "--output_dir  "+DIR_mapped,
        nucCov = "--nucleotide_coverage",
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(BOWTIE2) ,
        useBowtie2  = "--bowtie2 ",
        samtools    = "--samtools_path "+ os.path.dirname(SAMTOOLS),
        tempdir     = "--temp_dir "+PATHOUT
    log:
        PATHOUT+"04_mapped/{sample}_bismark_se_mapping.log"
    message: """-------------   Mapping single-end reads to genome {VERSION}. ------------- """
    shell:
        "nice -"+str(NICE)+" {BISMARK} {params} --multicore {threads} {input} 2> {log}"

#--------
rule bismark_pe:
    input:
        fin1 = DIR_trimmed+"{sample}"+RCODE+"1_val_1.fq.gz",
        fin2 = DIR_trimmed+"{sample}"+RCODE+"2_val_2.fq.gz"
    output:
        DIR_mapped+"{sample}"+RCODE+"1_val_1_bismark_bt2_pe.bam",
        DIR_mapped+"{sample}"+RCODE+"1_val_1_bismark_bt2_PE_report.txt"
    threads: 2
    params:
        bismark_genome_preparation_args = config.get("bismark_genome_preparation",""),
        genomeFolder = "--genome_folder " + GENOMEPATH,
        outdir = "--output_dir  "+DIR_mapped,
        nucCov = "--nucleotide_coverage",
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(BOWTIE2) ,
        useBowtie2  = "--bowtie2 ",
        samtools    = "--samtools_path "+ os.path.dirname(SAMTOOLS),
        tempdir     = "--temp_dir "+PATHOUT
    log:
        PATHOUT+"04_mapped/{sample}_bismark_pe_mapping.log"
    message: """-------------   Mapping paired-end reads to genome {VERSION}. ------------- """
    shell:
        "nice -"+str(NICE)+" {BISMARK} {params} --multicore {threads} -1 {input.fin1} -2 {input.fin2} 2> {log}"

# ==========================================================================================
# generate reference genome: ----  THIS ONLY GETS INVOKED WHEN MANUALLY CALLED SPECIFICIALLY ------

rule bismark_genome_preparation:
    input:
        GENOMEPATH
    output:
        GENOMEPATH+"Bisulfite_Genome/CT_conversion/genome_mfa.CT_conversion.fa",
        GENOMEPATH+"Bisulfite_Genome/GA_conversion/genome_mfa.GA_conversion.fa"
    params:
        bismark_genome_preparation_args = config.get("bismark_genome_preparation",""),
        pathToBowtie = "--path_to_bowtie "+ os.path.dirname(BOWTIE2) ,
        useBowtie2 = "--bowtie2 ",
        verbose = "--verbose "
    log:
        PATHOUT+'bismark_genome_preparation_'+VERSION+'.log'
    message: """ --------  converting {VERSION} Genome into Bisulfite analogue ------- """
    shell:
        "nice -"+str(NICE)+" {BISMARK_GENOME_PREPARATION} {params} {input} 2> {log}"

# # ==========================================================================================
# # post-trimming quality control

rule fastqc_after_trimming_se:
    input:
        DIR_trimmed+"{sample}_trimmed.fq.gz",
    output:
    	DIR_posttrim_QC+"{sample}_trimmed_fastqc.html",
    	DIR_posttrim_QC+"{sample}_trimmed_fastqc.zip"
    params:
        fastqc_args = config.get("fastqc_args", ""),
        outdir = "--outdir "+DIR_posttrim_QC
    log:
   	    DIR_posttrim_QC+"{sample}_trimmed_fastqc.log"
    message: """ ------------  Quality checking trimmmed single-end data with Fastqc ------------- """
    shell:
        "nice -"+str(NICE)+" {FASTQC} {params.outdir} {input} 2> {log}"
#--------
rule fastqc_after_trimming_pe:
    input:
        DIR_trimmed+"{sample}"+RCODE+"1_val_1.fq.gz",
        DIR_trimmed+"{sample}"+RCODE+"2_val_2.fq.gz"
    output:
    	DIR_posttrim_QC+"{sample}"+RCODE+"1_val_1_fastqc.html",
    	DIR_posttrim_QC+"{sample}"+RCODE+"1_val_1_fastqc.zip",
    	DIR_posttrim_QC+"{sample}"+RCODE+"2_val_2_fastqc.zip",
        DIR_posttrim_QC+"{sample}"+RCODE+"2_val_2_fastqc.html"
    params:
        fastqc_args = config.get("fastqc_args", ""),
        outdir = "--outdir "+DIR_posttrim_QC
    log:
   	    DIR_posttrim_QC+"{sample}_trimmed_fastqc.log"
    message: """ ------------  Quality checking trimmmed paired-end data with Fastqc ------------- """
    shell:
        "nice -"+str(NICE)+" {FASTQC} {params.outdir} {input} 2> {log}"
# #
# # ==========================================================================================
# # trim the reads

rule trimgalore_se:
   input:
       PATHIN+"{sample}"+INEXT
   output:
       DIR_trimmed+"{sample}_trimmed.fq.gz" #---- this ALWAYS outputs .fq.qz format.
#       DIR_trimmed+"{sample}"+INEXT+"_trimming_report.txt" #---@ commented out to avoid ambiguity: should find a way to put this back in while specififying it applies to any trimming report that does *NOT* contain "RCODE"
   params:
       extra          = config.get("trim_galore_args", ""),
       outdir = "--output_dir "+DIR_trimmed,
       phred = "--phred33",
       gz = "--gzip",
       cutadapt = "--path_to_cutadapt "+CUTADAPT,
   log:
       DIR_trimmed+"{sample}.trimgalore.log"
   message:
       " ---------  Trimming raw single-end read data using {TRIMGALORE} -------  "
   shell:
       "nice -"+str(NICE)+" {TRIMGALORE} {params} {input} 2> {log}"

#-----------------------
rule trimgalore_pe:
    input:
        PATHIN+"{sample}"+RCODE+"1"+INEXT,
        PATHIN+"{sample}"+RCODE+"2"+INEXT
    output:
        DIR_trimmed+"{sample}"+RCODE+"1_val_1.fq.gz", #---- this ALWAYS outputs .fq.qz format.
        DIR_trimmed+"{sample}"+RCODE+"2_val_2.fq.gz",
    params:
        extra          = config.get("trim_galore_args", ""),
        outdir         = "--output_dir "+DIR_trimmed,
        phred          = "--phred33",
        gz             = "--gzip",
        cutadapt       = "--path_to_cutadapt "+CUTADAPT,
        paired         = "--paired"
    log:
        DIR_trimmed+"{sample}.trimgalore.log"
    message:
        " ---------  Trimming raw paired-end read data using {TRIMGALORE} -------  "
    shell:
        "nice -"+str(NICE)+" {TRIMGALORE} {params} {input} 2> {log}"

# ==========================================================================================
# raw quality control

rule fastqc_raw: #----only need one: covers BOTH PE and SE cases.
    input:
        PATHIN+"{sample}"+INEXT
    output:
        DIR_rawqc+"{sample}_fastqc.html",
        DIR_rawqc+"{sample}_fastqc.zip"
    params:
        fastqc_args = config.get("fastqc_args", ""),
        outdir = "--outdir "+ DIR_rawqc     # usually pass params as strings instead of wildcards.

    log:
        PATHOUT+"01_rawqc/{sample}_fastqc.log"
    message: """ ----------  Quality checking raw read data with {FASTQC}.  --------------   """
    shell:
        "nice -"+str(NICE)+" {FASTQC} {params.outdir}  {input} 2> {log}"
