from pySM.src.model import Model

# create a model instance
# model settings automatically loaded
# eventual cleanup of previus databases in the case study path
# eventual generation of blank sets.xlsx file in the defined case study folder

test = Model(
    file_settings_name='model_settings.json',
    generate_sets_file=True
)

# after filling blank sets.xlsx, importing it in the model
test.database.load_sets()


# ancillary checks
# test.sets

