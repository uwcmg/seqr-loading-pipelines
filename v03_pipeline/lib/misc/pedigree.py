import hail as hl


def families_to_exclude(pedigree_ht: hl.Table, samples_ht: hl.Table) -> hl.Table:
    ht = pedigree_ht.key_by(pedigree_ht.s).anti_join(samples_ht)
    ht = ht.key_by(ht.family_id)
    ht = ht.distinct()
    return ht.select()


def families_to_include(pedigree_ht: hl.Table, samples_ht: hl.Table) -> hl.Table:
    ht = pedigree_ht.anti_join(families_to_exclude(pedigree_ht, samples_ht))
    ht = ht.distinct()
    return ht.select()


def samples_to_include(pedigree_ht: hl.Table, samples_ht: hl.Table) -> hl.Table:
    ht = pedigree_ht.join(families_to_include(pedigree_ht, samples_ht))
    ht = ht.key_by(ht.s)
    return ht.select()
