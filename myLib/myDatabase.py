from myLib.myLib import *
import psycopg2

class MyDatabase(metaclass=SingletonMeta):
    def __init__(self):
        self.database="template1"
        self.user="postgres"
        self.password="tanhungha"
        self.host="localhost"
        self.port="5432"
        
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

    def connect(self):
        try:
            
            self.conn = psycopg2.connect(
                                        database=self.database, 
                                        user=self.user, 
                                        password=self.password, 
                                        host=self.host, 
                                        port=self.port)
            
            self.cur = self.conn.cursor()
            log.info('Database connected')
        except psycopg2.Error as e:
            log.error(f"An error occurred when connect db: {e}")
            return False
        return True

    def disconnect(self):
        try:
            self.cur.close()
            self.conn.close()
            log.info('Database disconnected')
        except psycopg2.Error as e:
            log.error(f"An error occurred when disconnect db: {e}")
            return False
        return True
    
    
    def query(self, cmd):
        try:
            self.cur.execute(cmd)
            data = self.cur.fetchall()
        except psycopg2.Error as e:
            str = f"An error occurred when query db: {e}"
            log.error(str)
            return str
        return data
    
    def getPasswordLogin(self, username):
        try:
            table_name = 'accounts'
            cmd = f'SELECT "password" FROM "{self.schema_name}"."{table_name}" WHERE account = \'{username}\';'
            log.info(cmd)
            self.cur.execute(cmd)
            data = self.cur.fetchone()
            log.info(f'Query account {username}, password {data}')
        except psycopg2.Error as e:
            str = f"An error occurred when query db: {e}"
            log.error(str)
            return None
        return data