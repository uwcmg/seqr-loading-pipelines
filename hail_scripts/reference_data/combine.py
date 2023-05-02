import functools
import re
from datetime import datetime

import hail as hl

from hail_scripts.reference_data.config import CONFIG

ENUM_MAPPABLE_TYPES = {hl.tarray(hl.tstr), hl.tset(hl.tstr)}


def get_select_fields(selects, base_ht):
    """
    Generic function that takes in a select config and base_ht and generates a
    select dict that is generated from traversing the base_ht and extracting the right
    annotation. If '#' is included at the end of a select field, the appropriate
    biallelic position will be selected (e.g. 'x#' -> x[base_ht.a_index-1].
    :param selects: mapping or list of selections
    :param base_ht: base_ht to traverse
    :return: select mapping from annotation name to base_ht annotation
    """
    select_fields = {}
    if selects is not None:
        if isinstance(selects, list):
            select_fields = {selection: base_ht[selection] for selection in selects}
        elif isinstance(selects, dict):
            for key, val in selects.items():
                # Grab the field and continually select it from the hail table.
                ht = base_ht
                for attr in val.split('.'):
                    # Select from multi-allelic list.
                    if attr.endswith('#'):
                        attr = attr[:-1]
                        ht = ht[attr][base_ht.a_index - 1]
                    else:
                        ht = ht[attr]
                select_fields[key] = ht
    return select_fields


def get_enum_select_fields(enum_selects, ht):
    enum_select_fields = {}
    if enum_selects is None:
        return enum_select_fields
    for field_name, values in enum_selects.items():
        lookup = hl.dict(hl.enumerate(values, index_first=False))
        # NB: this conditioning on type is "outside" the hail expression context.
        if ht[field_name].dtype in ENUM_MAPPABLE_TYPES:
            enum_select_fields[f'{field_name}_ids'] = ht[field_name].map(lambda x: lookup[x])
        else:
            enum_select_fields[f'{field_name}_id'] = lookup[ht[field_name]]
    return enum_select_fields


def get_ht(dataset, reference_genome):
    'Returns the appropriate deduped hail table with selects applied.'
    config = CONFIG[dataset][reference_genome]
    print(f"Reading in {dataset}")
    base_ht = hl.read_table(config['path'])

    if config.get('filter'):
        base_ht = base_ht.filter(config['filter'](base_ht))

    # 'select' and 'custom_select's to generate dict.
    select_fields = get_select_fields(config.get('select'), base_ht)
    if 'custom_select' in config:
        select_fields = {**select_fields, **config['custom_select'](base_ht)}

    select_query = {dataset: hl.struct(**select_fields)}

    print(select_fields)
    # First pass with selects and custom_selects
    ht = base_ht.select(**select_fields).distinct()

    # Second pass will transmute w/ the mapped enum
    enum_select_fields = get_enum_select_fields(config.get('enum_select'), ht)
    ht = ht.transmute(**enum_select_fields)
    
    # Last pass will nest the selected fields (except for the key) in a struct
    return ht.select(**{field_name: ht.row.drop(*ht.key)})


def update_joined_ht_globals(
    joined_ht, datasets, version, reference_genome
):
    # Track the dataset we've added as well as the source path.
    included_dataset = {
        k: v[reference_genome]['path']
        for k, v in CONFIG.items()
        if k in datasets
    }
    enum_definitions = {
        k: {enum_field_name: enum_values}
        for k, v in CONFIG.items()
        if k in datasets
        if 'enum_select' in v[reference_genome]
        for enum_field_name, enum_values in v[reference_genome]['enum_select'].items()
    }
    # Add metadata, but also removes previous globals.
    return joined_ht.select_globals(
        date=datetime.now().isoformat(),
        datasets=hl.dict(included_dataset),
        version=version,
        enum_definitions=hl.dict(enum_definitions),
    )


def join_hts(datasets, version, reference_genome='37'):
    # Get a list of hail tables and combine into an outer join.
    hts = [get_ht(dataset, reference_genome) for dataset in datasets]
    joined_ht = functools.reduce(
        (lambda joined_ht, ht: joined_ht.join(ht, 'outer')), hts
    )

    joined_ht = update_joined_ht_globals(
        joined_ht, datasets, version, reference_genome
    )
    joined_ht.describe()
    return joined_ht
