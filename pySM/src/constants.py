"""Basic constants for definition of model structure"""

# basic package information
_INFO = {
    'Package name': 'pySM',
    'Description': 'Python-based general purpose Systems Modeller',
    'Author': 'Matteo V. Rocco'
}

# structure of the sets of the model
_SETS = {

    'REGIONS': {
        'Symbol': 'r',
        'Categories': ['Productive system', 'Other systems', 'Environment'],
        'Headers': ['ID', 'Category', 'Name', 'Cluster_1']
    },

    'TECHNOLOGIES': {
        'Symbol': 't',
        'Categories': {
            'Supply': ['Production', 'Storage', 'Transmission'],
            'Demand': ['Demand']
        },
        'Headers': ['ID', 'Category', 'Category_spec', 'Name', 'Cluster_1']
    },

    'FLOWS': {
        'Symbol': 'f',
        'Categories': ['Product flow', 'Production factor', 'Environmental transaction'],
        'Headers': ['ID', 'Category', 'Unit', 'Name', 'Cluster_1']
    }

}

# structure of the generic case study folder
_FOLDERS = ['']
