import hail as hl
import luigi

from v03_pipeline.lib.misc.io import write
from v03_pipeline.lib.model import DatasetType, Env, ReferenceGenome, SampleType
from v03_pipeline.lib.tasks.files import GCSorLocalFolderTarget


class BaseWriteTask(luigi.Task):
    reference_genome = luigi.EnumParameter(enum=ReferenceGenome)
    dataset_type = luigi.EnumParameter(enum=DatasetType)
    sample_type = luigi.EnumParameter(enum=SampleType)

    def output(self) -> luigi.Target:
        raise NotImplementedError

    def complete(self) -> bool:
        return GCSorLocalFolderTarget(self.output().path).exists()

    def init_hail(self):
        # Need to use the GCP bucket as temp storage for very large callset joins
        hl.init(tmp_dir=Env.HAIL_TMPDIR, idempotent=True)

        # Interval ref data join causes shuffle death, this prevents it
        hl._set_flags(use_new_shuffle='1', no_whole_stage_codegen='1')  # noqa: SLF001

    def run(self) -> None:
        self.init_hail()
        ht = self.create_table()
        write(ht, self.output().path)

    def create_table(self) -> hl.Table:
        raise NotImplementedError
