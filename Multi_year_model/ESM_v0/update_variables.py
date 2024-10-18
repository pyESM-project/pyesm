#%%
# Load the YAML content
import yaml
import ruamel.yaml
input_file = 'structure_variables.yml'
output_file = 'structure_variables_new.yml'

yaml = ruamel.yaml.YAML()

yaml.preserve_quotes = True

 

with open(input_file, 'r') as file:

    data: dict = yaml.load(file)

#%%

# Function to transform the variables_info structure

def transform_variables_info(variables_info: dict):

    transformed_info = {}

    for key, value in variables_info.items():

        if value is None or {}:

            transformed_info[key] = None

            continue

        value: dict

        transformed_info[key] = {}

        for inner_key, inner_value in value.items():

            if inner_key == 'value':

                transformed_info[key]['value'] = inner_value

            if isinstance(inner_value, dict):

                if 'set' in inner_value:

                    new_key = inner_value['set']

                    transformed_info[key][new_key] = {'dim': inner_key}

                if 'filters' in inner_value:

                    transformed_info[key][new_key]['filters'] = inner_value['filters']

    return transformed_info

#%%

# Apply the transformation to each item in the dictionary

for key, value in data.items():

    if 'variables_info' in value and isinstance(value['variables_info'], dict):

        value['variables_info'] = transform_variables_info(value['variables_info'])

 

# Write the modified content back to the YAML file

with open(output_file, 'w') as file:

    yaml.dump(data, file)

 

 
# %%
