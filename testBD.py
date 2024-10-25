# import psycopg2

# # Connect to the database
# conn = psycopg2.connect(database="template1", user="postgres", 
#                         password="tanhungha", host="localhost", port="5432")
# cur = conn.cursor()

# # Specify the schema and table name
# schema_name = 'assetDB'
# table_name = 'orderdetail'  # Ensure this matches the exact name in the database
# table_name = 'accounts'

# # SQL query to select all data from the specified table in the specified schema
# cmd = f'SELECT * FROM "{schema_name}"."{table_name}";'

# try:

#     print(cmd)
#     cur.execute(cmd)
#     data = cur.fetchall()

#     # Print the fetched data
#     for row in data:
#         print(row)

# except psycopg2.Error as e:
#     print(f"An error occurred: {e}")

# finally:
#     cur.close()
#     conn.close()


from myLib.myDatabase import MyDatabase
from myLib.myLib import *

tuanDB = MyDatabase()

if tuanDB.connect():
    print("Connected")
        # Specify the schema and table name
    schema_name = 'assetDB'
    table_name = 'orderdetail'  # Ensure this matches the exact name in the database
    table_name = 'accounts'

    # SQL query to select all data from the specified table in the specified schema
    cmd = f'SELECT * FROM "{schema_name}"."{table_name}";'

    xxx = tuanDB.query(cmd)
    print(xxx)

    tuanDB.disconnect()
else:
    print("Error")
