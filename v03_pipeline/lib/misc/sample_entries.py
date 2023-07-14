import hail as hl


def globalize_sample_ids(ht: hl.Table) -> hl.Table:
    ht = ht.annotate_globals(
        sample_ids=ht.aggregate(hl.agg.take(ht.entries.sample_id, 1)[0]),
    )
    return ht.annotate(entries=ht.entries.map(lambda s: s.drop('sample_id')))


def deglobalize_sample_ids(ht: hl.Table) -> hl.Table:
    ht = ht.annotate(
        entries=(
            hl.zip_with_index(ht.entries).starmap(
                lambda i, e: hl.Struct(**e, sample_id=ht.sample_ids[i]),
            )
        ),
    )
    return ht.drop('sample_ids')

def remove_callset_sample_ids(
    sample_lookup_ht: hl.Table,
    sample_subset_ht: hl.Table,
) -> hl.Table:
    sample_ids = sample_subset_ht.aggregate(hl.agg.collect_as_set(sample_subset_ht.s))
    return ht.annotate(
        entries=(
            ht.entries.filter(lambda e: ~hl.set(sample_ids).contains(e.sample_id))
        ),
    )

def union_entries_hts(ht: hl.Table, callset_ht: hl.Table) -> hl.Table:
    ht_empty_entries = hl.empty_array(ht.entries.dtype.element_type)
    callset_ht_empty_entries = _hl.empty_array(callset_ht.entries.dtype.element_type)
    ht = ht.join(callset_ht, 'outer')
    return ht.select(
        filters=hl.or_else(ht.filters_1, ht.filters),
        entries=(
            hl.case()
            .when(hl.is_missing(ht.entries), ht_empty_entries.extend(ht.entries_1))
            .when(
                hl.is_missing(ht.entries_1),
                ht.entries.extend(callset_ht_empty_entries),
            )
            .default(ht.entries.extend(ht.entries_1))
        ),
    )
