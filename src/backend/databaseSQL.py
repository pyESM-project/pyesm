class DatabaseSQL():

    def __init__(self):
        pass

    def generate_blank_database_sql(
            self,
            database_sql_name: str = 'database.db',
    ) -> None:

        self.database_sql_name = database_sql_name
        self.database_sql_path = Path(
            self.database_dir_path, database_sql_name)

        self.data_sql = DatabaseSQL(
            logger=self.logger,
            database_sql_path=self.database_sql_path,
        )

        for table in self.sets_structure:
            self.data_sql.create_table(
                table_name=self.sets_structure[table]['table_name'],
                table_fields=self.sets_structure[table]['table_headers']
            )
