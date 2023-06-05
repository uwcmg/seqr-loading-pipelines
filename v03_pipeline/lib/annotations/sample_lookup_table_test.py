import unittest

import hail as hl

from v03_pipeline.lib.annotations.sample_lookup_table import AC, AF, AN, hom


class SampleLookupTableAnnotationsTest(unittest.TestCase):
    def test_allele_count_annotations(self) -> None:
        ht = hl.Table.parallelize(
            [
                {
                    'id': 0,
                },
            ],
            hl.tstruct(
                id=hl.tint32,
            ),
            key='id',
        )
        sample_lookup_ht = hl.Table.parallelize(
            [
                {
                    'id': 0,
                    'ref_samples': {'a', 'c'},
                    'het_samples': {'b', 'd'},
                    'hom_samples': {'e', 'f'},
                },
            ],
            hl.tstruct(
                id=hl.tint32,
                ref_samples=hl.tset(hl.tstr),
                het_samples=hl.tset(hl.tstr),
                hom_samples=hl.tset(hl.tstr),
            ),
            key='id',
        )
        ht = ht.select(
            AC=AC(ht, sample_lookup_ht),
            AF=AF(ht, sample_lookup_ht),
            AN=AN(ht, sample_lookup_ht),
            hom=hom(ht, sample_lookup_ht),
        )
        self.assertCountEqual(
            ht.collect(),
            [
                hl.Struct(id=0, AC=6, AF=0.5, AN=12, hom=2),
            ],
        )
