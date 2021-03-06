"""Variant calling support for Sentieon tools.

Sentieon provides optimized versions of standard tools like GATK HaplotypeCaller
and MuTect2 as well as their own developed versions. These require a license
from Sentieon for use:

http://sentieon.com/about/
https://peerj.com/preprints/1672/
"""
import os
from bcbio import utils
from bcbio.distributed.transaction import file_transaction
from bcbio.pipeline import config_utils, shared
from bcbio.pipeline import datadict as dd
from bcbio.provenance import do
from bcbio.variation import bamprep, bedutils, vcfutils

def license_export(data):
    """Retrieve export statement for sentieon license server.
    """
    resources = config_utils.get_resources("sentieon", data["config"])
    server = resources.get("keyfile")
    if not server:
        raise ValueError("Need to set resources keyfile with URL:port of license server, local license file or "
                         "environmental variables to export \n"
                         "http://bcbio-nextgen.readthedocs.io/en/latest/contents/configuration.html#resources")
    if isinstance(server, basestring):
        return "export SENTIEON_LICENSE=%s && " % server
    else:
        assert isinstance(server, dict), server
        exports = ""
        for key, val in server.items():
            exports += "export %s=%s && " % (key.upper(), val)
        return exports

def _get_interval(variant_regions, region, out_file, items):
    """Retrieve interval to run analysis in. Handles no targets, BED and regions
    """
    target = shared.subset_variant_regions(variant_regions, region, out_file, items)
    if target:
        if isinstance(target, basestring) and os.path.isfile(target):
            return "--interval %s" % target
        else:
            return "--interval %s" % bamprep.region_to_gatk(target)
    else:
        return ""

def run_tnscope(align_bams, items, ref_file, assoc_files,
                     region=None, out_file=None):
    """Call variants with Sentieon's TNscope somatic caller.
    """
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % utils.splitext_plus(align_bams[0])[0]
    if not utils.file_exists(out_file):
        variant_regions = bedutils.merge_overlaps(dd.get_variant_regions(items[0]), items[0])
        interval = _get_interval(variant_regions, region, out_file, items)
        with file_transaction(items[0], out_file) as tx_out_file:
            paired = vcfutils.get_paired_bams(align_bams, items)
            assert paired and paired.normal_bam, "Require normal BAM for Sentieon TNscope"
            dbsnp = "--dbsnp %s" % (assoc_files.get("dbsnp")) if "dbsnp" in assoc_files else ""
            license = license_export(items[0])
            cmd = ("{license}sentieon driver -t 1 -r {ref_file} "
                   "-i {paired.tumor_bam} -i {paired.normal_bam} {interval} "
                   "--algo TNscope "
                   "--tumor_sample {paired.tumor_name} --normal_sample {paired.normal_name} "
                   "{dbsnp} {tx_out_file}")
            do.run(cmd.format(**locals()), "Sentieon TNhaplotyper")
    return out_file

def run_tnhaplotyper(align_bams, items, ref_file, assoc_files,
                     region=None, out_file=None):
    """Call variants with Sentieon's TNhaplotyper (MuTect2 like).
    """
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % utils.splitext_plus(align_bams[0])[0]
    if not utils.file_exists(out_file):
        variant_regions = bedutils.merge_overlaps(dd.get_variant_regions(items[0]), items[0])
        interval = _get_interval(variant_regions, region, out_file, items)
        with file_transaction(items[0], out_file) as tx_out_file:
            paired = vcfutils.get_paired_bams(align_bams, items)
            assert paired.normal_bam, "Require normal BAM for Sentieon TNhaplotyper"
            dbsnp = "--dbsnp %s" % (assoc_files.get("dbsnp")) if "dbsnp" in assoc_files else ""
            cosmic = "--cosmic %s" % (assoc_files.get("cosmic")) if "cosmic" in assoc_files else ""
            license = license_export(items[0])
            cmd = ("{license}sentieon driver -t 1 -r {ref_file} "
                   "-i {paired.tumor_bam} -i {paired.normal_bam} {interval} "
                   "--algo TNhaplotyper "
                   "--tumor_sample {paired.tumor_name} --normal_sample {paired.normal_name} "
                   "{dbsnp} {cosmic} {tx_out_file}")
            do.run(cmd.format(**locals()), "Sentieon TNhaplotyper")
    return out_file

def run_haplotyper(align_bams, items, ref_file, assoc_files,
                     region=None, out_file=None):
    """Call variants with Sentieon's haplotyper (GATK HaplotypeCaller like).
    """
    if out_file is None:
        out_file = "%s-variants.vcf.gz" % utils.splitext_plus(align_bams[0])[0]
    if not utils.file_exists(out_file):
        variant_regions = bedutils.merge_overlaps(dd.get_variant_regions(items[0]), items[0])
        interval = _get_interval(variant_regions, region, out_file, items)
        with file_transaction(items[0], out_file) as tx_out_file:
            dbsnp = "--dbsnp %s" % (assoc_files.get("dbsnp")) if "dbsnp" in assoc_files else ""
            bams = " ".join(["-i %s" % x for x in align_bams])
            license = license_export(items[0])
            cmd = ("{license}sentieon driver -t 1 -r {ref_file} "
                   "{bams} {interval} --algo Haplotyper {dbsnp} {tx_out_file}")
            do.run(cmd.format(**locals()), "Sentieon TNhaplotyper")
    return out_file
