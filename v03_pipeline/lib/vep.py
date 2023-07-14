from __future__ import annotations

import hail as hl

import luigi_pipeline.lib.hail_vep_runners as vep_runners
from v03_pipeline.lib.model import DatasetType, Env, ReferenceGenome

BIOTYPES = [
    'IG_C_gene',
    'IG_D_gene',
    'IG_J_gene',
    'IG_LV_gene',
    'IG_V_gene',
    'TR_C_gene',
    'TR_J_gene',
    'TR_V_gene',
    'TR_D_gene',
    'IG_pseudogene',
    'IG_C_pseudogene',
    'IG_J_pseudogene',
    'IG_V_pseudogene',
    'TR_V_pseudogene',
    'TR_J_pseudogene',
    'Mt_rRNA',
    'Mt_tRNA',
    'miRNA',
    'misc_RNA',
    'rRNA',
    'scRNA',
    'snRNA',
    'snoRNA',
    'ribozyme',
    'sRNA',
    'scaRNA',
    'lncRNA',
    'Mt_tRNA_pseudogene',
    'tRNA_pseudogene',
    'snoRNA_pseudogene',
    'snRNA_pseudogene',
    'scRNA_pseudogene',
    'rRNA_pseudogene',
    'misc_RNA_pseudogene',
    'miRNA_pseudogene',
    'TEC',
    'nonsense_mediated_decay',
    'non_stop_decay',
    'retained_intron',
    'protein_coding',
    'protein_coding_LoF',
    'protein_coding_CDS_not_defined',
    'processed_transcript',
    'non_coding',
    'ambiguous_orf',
    'sense_intronic',
    'sense_overlapping',
    'antisense/antisense_RNA',
    'antisense',
    'known_ncrna',
    'pseudogene',
    'processed_pseudogene',
    'polymorphic_pseudogene',
    'retrotransposed',
    'transcribed_processed_pseudogene',
    'transcribed_unprocessed_pseudogene',
    'transcribed_unitary_pseudogene',
    'translated_processed_pseudogene',
    'translated_unprocessed_pseudogene',
    'unitary_pseudogene',
    'unprocessed_pseudogene',
    'artifact',
    'lincRNA',
    'lincrna',
    'macro_lncRNA',
    '3prime_overlapping_ncRNA',
    'disrupted_domain',
    'vaultRNA/vault_RNA',
    'vaultRNA',
    'bidirectional_promoter_lncRNA',
]

CONSEQUENCE_TERMS = [
    'transcript_ablation',
    'splice_acceptor_variant',
    'splice_donor_variant',
    'stop_gained',
    'frameshift_variant',
    'stop_lost',
    'start_lost',  # new in v81
    'initiator_codon_variant',  # deprecated
    'transcript_amplification',
    'inframe_insertion',
    'inframe_deletion',
    'missense_variant',
    'protein_altering_variant',  # new in v79
    'splice_region_variant',
    'incomplete_terminal_codon_variant',
    'start_retained_variant',
    'stop_retained_variant',
    'synonymous_variant',
    'coding_sequence_variant',
    'mature_miRNA_variant',
    '5_prime_UTR_variant',
    '3_prime_UTR_variant',
    'non_coding_transcript_exon_variant',
    'non_coding_exon_variant',  # deprecated
    'intron_variant',
    'NMD_transcript_variant',
    'non_coding_transcript_variant',
    'nc_transcript_variant',  # deprecated
    'upstream_gene_variant',
    'downstream_gene_variant',
    'TFBS_ablation',
    'TFBS_amplification',
    'TF_binding_site_variant',
    'regulatory_region_ablation',
    'regulatory_region_amplification',
    'feature_elongation',
    'regulatory_region_variant',
    'feature_truncation',
    'intergenic_variant',
]

LOF_FILTERS = [
    'END_TRUNC',
    'INCOMPLETE_CDS',
    'EXON_INTRON_UNDEF',
    'SMALL_INTRON',
    'ANC_ALLELE',
    'NON_DONOR_DISRUPTING',
    'NON_ACCEPTOR_DISRUPTING',
    'RESCUE_DONOR',
    'RESCUE_ACCEPTOR',
    'GC_TO_GT_DONOR',
    '5UTR_SPLICE',
    '3UTR_SPLICE',
]


def annotate_sorted_transcript_consequences_enums(ht: hl.Table) -> hl.Table:
    return ht.annotate_globals(
        paths=hl.Struct(
            **ht.paths,
            sorted_transcript_consequences=hl.missing(hl.tstr),
        ),
        versions=hl.Struct(
            **ht.versions,
            sorted_transcript_consequences=hl.missing(hl.tstr),
        ),
        enums=hl.Struct(
            **ht.enums,
            sorted_transcript_consequences=hl.Struct(
                biotype=BIOTYPES,
                consequence_term=CONSEQUENCE_TERMS,
                lof_filter=LOF_FILTERS,
            ),
        ),
    )


def run_vep(
    mt: hl.Table,
    env: Env,
    reference_genome: ReferenceGenome,
    dataset_type: DatasetType,
    vep_config_json_path: str | None,
) -> hl.Table:
    if hasattr(mt, 'vep') or not dataset_type.veppable:
        return mt
    vep_runner = (
        vep_runners.HailVEPRunner()
        if env != Env.TEST
        else vep_runners.HailVEPDummyRunner()
    )
    return vep_runner.run(
        mt,
        reference_genome.v02_value,
        vep_config_json_path=vep_config_json_path,
    )
