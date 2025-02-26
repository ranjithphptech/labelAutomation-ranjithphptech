import mysql.connector
import configparser

config = configparser.ConfigParser()
config.read('config.ini')

SERVICE_NAME = config['database']['host']
LDAP_SERVER_IP = config['database']['host']  

config = {
    "host": config['database']['host'],
    "port": config['database']['port'],
    "user": config['database']['user'],
    "password": config['database']['password'],
    "use_pure": True,
    "krb_service_principal": f"{SERVICE_NAME}/{LDAP_SERVER_IP}",
    "database": config['database']['databaseName'],
}

try:    
    conn = mysql.connector.connect(**config) 
    
    if conn.is_connected():
        print("Connection established successfully!")
        
except mysql.connector.Error as err:
    print(f"Error: {err}")

