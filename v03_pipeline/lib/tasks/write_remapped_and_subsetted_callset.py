import hail as hl
import luigi

from v03_pipeline.lib.misc.family_loading_failures import (
    get_families_failed_missing_samples,
    get_families_failed_relatedness_check,
    get_families_failed_sex_check,
)
from v03_pipeline.lib.misc.io import does_file_exist, import_pedigree, import_remap
from v03_pipeline.lib.misc.pedigree import parse_pedigree_ht_to_families
from v03_pipeline.lib.misc.sample_ids import remap_sample_ids, subset_samples
from v03_pipeline.lib.model import Env
from v03_pipeline.lib.paths import remapped_and_subsetted_callset_path
from v03_pipeline.lib.tasks.base.base_write_task import BaseWriteTask
from v03_pipeline.lib.tasks.files import GCSorLocalTarget, RawFileTask
from v03_pipeline.lib.tasks.write_imported_callset import WriteImportedCallsetTask
from v03_pipeline.lib.tasks.write_relatedness_check_table import (
    WriteRelatednessCheckTableTask,
)
from v03_pipeline.lib.tasks.write_sex_check_table import WriteSexCheckTableTask


class WriteRemappedAndSubsettedCallsetTask(BaseWriteTask):
    callset_path = luigi.Parameter()
    project_guid = luigi.Parameter()
    project_remap_path = luigi.Parameter()
    project_pedigree_path = luigi.Parameter()
    ignore_missing_samples_when_subsetting = luigi.BoolParameter(
        default=False,
        parsing=luigi.BoolParameter.EXPLICIT_PARSING,
    )
    ignore_missing_samples_when_remapping = luigi.BoolParameter(
        default=False,
        parsing=luigi.BoolParameter.EXPLICIT_PARSING,
    )
    validate = luigi.BoolParameter(
        default=True,
        parsing=luigi.BoolParameter.EXPLICIT_PARSING,
    )

    def output(self) -> luigi.Target:
        return GCSorLocalTarget(
            remapped_and_subsetted_callset_path(
                self.reference_genome,
                self.dataset_type,
                self.callset_path,
                self.project_guid,
            ),
        )

    def requires(self) -> list[luigi.Task]:
        requirements = [
            WriteImportedCallsetTask(
                self.reference_genome,
                self.dataset_type,
                self.sample_type,
                self.callset_path,
                # NB: filters_path is explicitly passed as None here
                # to avoid carrying it throughout the rest of the pipeline.
                # Only the primary import task itself should be aware of it.
                None,
                self.validate,
            ),
            RawFileTask(self.project_pedigree_path),
        ]
        if (
            Env.CHECK_SEX_AND_RELATEDNESS
            and self.dataset_type.check_sex_and_relatedness
        ):
            requirements = [
                *requirements,
                WriteRelatednessCheckTableTask(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.callset_path,
                ),
                WriteSexCheckTableTask(
                    self.reference_genome,
                    self.dataset_type,
                    self.sample_type,
                    self.callset_path,
                ),
            ]
        return requirements

    def create_table(self) -> hl.MatrixTable:
        callset_mt = hl.read_matrix_table(self.input()[0].path)
        pedigree_ht = import_pedigree(self.input()[1].path)

        # Remap, but only if the remap file is present!
        remap_lookup = hl.empty_dict(hl.tstr, hl.tstr)
        if does_file_exist(self.project_remap_path):
            project_remap_ht = import_remap(self.project_remap_path)
            callset_mt = remap_sample_ids(
                callset_mt,
                project_remap_ht,
                self.ignore_missing_samples_when_remapping,
            )
            remap_lookup = hl.dict(
                {r.s: r.seqr_id for r in project_remap_ht.collect()},
            )

        families = parse_pedigree_ht_to_families(pedigree_ht)
        families_failed_missing_samples = get_families_failed_missing_samples(
            callset_mt,
            families,
        )
        families_failed_relatedness_check = set()
        families_failed_sex_check = set()
        if (
            Env.CHECK_SEX_AND_RELATEDNESS
            and self.dataset_type.check_sex_and_relatedness
        ):
            relatedness_check_ht = hl.read_table(self.input()[2].path)
            sex_check_ht = hl.read_table(self.input()[3].path)
            families_failed_relatedness_check = get_families_failed_relatedness_check(
                families,
                relatedness_check_ht,
                remap_lookup,
            )
            families_failed_sex_check = get_families_failed_sex_check(
                families,
                sex_check_ht,
                remap_lookup,
            )

        loadable_families = (
            families
            - families_failed_missing_samples
            - families_failed_relatedness_check
            - families_failed_sex_check
        )
        if not len(loadable_families):
            msg = 'All families failed checks'
            raise RuntimeError(msg)

        mt = subset_samples(
            callset_mt,
            hl.Table.parallelize(
                [
                    {'s': sample_id}
                    for family in loadable_families
                    for sample_id in family.samples
                ],
                hl.tstruct(s=hl.dtype('str')),
                key='s',
            ),
            self.ignore_missing_samples_when_subsetting,
        )
        return mt.select_globals(
            family_guids_failed_missing_samples=(
                {f.family_guid for f in families_failed_missing_samples}
                or hl.empty_set(hl.tstr)
            ),
            family_guids_failed_relatedness_check=(
                {f.family_guid for f in families_failed_relatedness_check}
                or hl.empty_set(hl.tstr)
            ),
            family_guids_failed_sex_check=(
                {f.family_guid for f in families_failed_sex_check}
                or hl.empty_set(hl.tstr)
            ),
            families=(
                {
                    f.family_guid: sorted(f.samples.keys())
                    for f in loadable_families
                    or hl.empty_dict(hl.tstr, hl.tarray(hl.tstr))
                }
            ),
        )
