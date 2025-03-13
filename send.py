import os
import shutil
import psutil

import pika
import json
import time
import configparser

current_file_path = os.path.dirname(os.path.abspath(__file__))

# def is_process_running(pid):
#     return psutil.pid_exists(pid)

# senpid = current_file_path+'\sendpid.txt'
# check_file = os.path.isfile(senpid)
# if check_file:
#     pid=''
#     with open(senpid, "r") as file:
#          pid = int(file.read())
   
#     if is_process_running(pid):
#         print(f"Process with PID {pid} is running.")
#         exit()
#     else:
#         print(f"Process with PID {pid} is not running.")
#         pid = str(os.getpid())
#         print(f"Process with PID {pid} is running.")
#         with open(senpid, "w") as file:
#             file.write(pid)
# else:
#     pid = str(os.getpid())
#     with open(senpid, "w") as file:
#         file.write(pid)
#     print(f"Process with PID {pid} is running.")


config = configparser.ConfigParser()
config.read(current_file_path+'/config.ini')
newOrderDir = current_file_path+"/"+config['paths']['newOrderDir']
orderProcessing = current_file_path+"/"+config['paths']['orderProcessing']
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='localhost',heartbeat=1800))
channel = connection.channel()

channel.queue_declare(queue='LabelAutomation',durable=True)
print(" [*] Waiting for order. To exit press CTRL+C")
while True:
    for zipFile in os.listdir(newOrderDir):
        baseNameofZip = os.path.splitext(zipFile)[0]        
        shutil.move(newOrderDir+'/'+baseNameofZip+'.zip', orderProcessing+'/'+baseNameofZip+'.zip')
        d = {
            "service": "artwork_customer_approval",
            "order": baseNameofZip
            }
        channel.basic_publish(
            exchange='', 
            routing_key='LabelAutomation', 
            body=json.dumps(d),
            properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
            )
        print("Order sent for processing "+zipFile)
    time.sleep(5)   
        
connection.close()