from flask_restful import Resource
from flask import request
from myLib.myDatabase import MyDatabase
from decimal import Decimal
from datetime import datetime

myDatabase = MyDatabase()

def convert_special_types(value):
    """Chuyển đổi các kiểu dữ liệu không tuần tự hóa được sang định dạng có thể tuần tự hóa."""
    if isinstance(value, Decimal):
        return float(value)  # Chuyển Decimal thành float
    elif isinstance(value, datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')  # Chuyển datetime thành chuỗi
    return value  # Giữ nguyên nếu không phải kiểu đặc biệt

class QueryData(Resource):
    def post(self):
        sql_query = request.get_json().get('sql_query', '')
        if not sql_query.strip().upper().startswith("SELECT"):
            return {'error': 'Only SELECT queries are allowed'}, 400

        if myDatabase.ensure_connection():
            try:
                columns, result = myDatabase.query2(sql_query)
                if isinstance(columns, str) and "An error occurred" in columns:
                    return {'error': columns}, 400
                elif not columns:
                    return {'message': 'Query executed successfully'}, 200
                else:
                    # Chuyển đổi dữ liệu thành định dạng có thể tuần tự hóa
                    converted_result = [
                        {columns[i]: convert_special_types(row[i]) for i in range(len(columns))}
                        for row in result
                    ]
                    return {'columns': columns, 'data': converted_result}, 200
            except Exception as e:
                return {'error': str(e)}, 500
            finally:
                myDatabase.disconnect()
        else:
            return {'error': 'Database connection failed'}, 500
