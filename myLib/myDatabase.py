from myLib.myLib import *
import psycopg2

class MyDatabase(metaclass=SingletonMeta):
    def __init__(self):
        self.database = "template1"
        self.user = "postgres"
        self.password = "tanhungha"
        self.host = "192.168.100.100"
        self.port = "5432"
        
        # Specify the schema and table name
        self.schema_name = 'assetDB'
        self.table_name = ['packings', 
                           'warehouses', 
                           'locations',
                           'units', 
                           'permissions', 
                           'users', 
                           'departments', 
                           'products', 
                           'prdstatus', 
                           'orderdetail', 
                           'categories',
                           'accounts']
        
        # SQL query to select all data from the specified table in the specified schema
        # table = f'"{self.schema_name}"."{self.table_name[0]}";'

        # Connect to the database
        self.conn = None
        self.cur = None

    def ensure_connection(self):
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(
                    database=self.database, 
                    user=self.user, 
                    password=self.password, 
                    host=self.host, 
                    port=self.port
                )
                self.cur = self.conn.cursor()
                log.info('Database connected')
            except psycopg2.Error as e:
                log.error(f"An error occurred when connecting to db: {e}")
                return False
        return True

    def disconnect(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        self.cur = None
        self.conn = None
        log.info('Database disconnected')

    def query(self, cmd):
        try:
            self.cur.execute(cmd)
            data = self.cur.fetchall()
        except psycopg2.Error as e:
            str = f"An error occurred when query db: {e}"
            log.error(str)
            return str
        return data

    def query2(self, cmd):
        if not self.ensure_connection():
            return "Failed to connect to database", None

        try:
            self.cur.execute(cmd)
            log.info(cmd)
            sql_command = cmd.strip().upper()
            
            if sql_command.startswith('SELECT'):
                columns = [desc[0] for desc in self.cur.description]
                data = self.cur.fetchall()
                log.info(f'  Data:{data}')
                return columns, data
            elif sql_command.startswith('INSERT') and 'RETURNING' in sql_command:
                self.conn.commit()
                return self.cur.fetchone(), None
            elif sql_command.startswith(('INSERT', 'UPDATE', 'DELETE')):
                self.conn.commit()
                return "Query executed successfully", None
            else:
                return "Query executed without fetching data", None

        except psycopg2.Error as e:
            self.conn.rollback()
            error_msg = f"An error occurred when querying the db: {e}"
            log.error(error_msg)
            return error_msg, None

    def getPasswordLogin(self, username):
        if not self.ensure_connection():
            return None

        try:
            table_name = 'accounts'
            cmd = f'SELECT "password" FROM "{self.schema_name}"."{table_name}" WHERE account = %s;'
            self.cur.execute(cmd, (username,))
            data = self.cur.fetchone()
            log.info(f'Query account {username}, password {data}')
            return data
        except psycopg2.Error as e:
            log.error(f"An error occurred when querying db: {e}")
            return None

    def get_table_names(self):
        if not self.ensure_connection():
            return []

        try:
            cmd = f"""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = %s 
            AND table_type = 'BASE TABLE';
            """
            self.cur.execute(cmd, (self.schema_name,))
            tables = [row[0] for row in self.cur.fetchall()]
            return tables
        except psycopg2.Error as e:
            log.error(f"An error occurred when fetching table names: {e}")
            return []
