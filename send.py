import os
import shutil
import json
import time
import configparser
import pika

def main():
    current_file_path = os.path.dirname(os.path.abspath(__file__))

    config = configparser.ConfigParser()
    config.read(os.path.join(current_file_path, 'config.ini'))
    new_order_dir = os.path.join(current_file_path, config['paths']['newOrderDir'])
    order_processing_dir = os.path.join(current_file_path, config['paths']['orderProcessing'])

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='localhost', heartbeat=1800))
    channel = connection.channel()

    channel.queue_declare(queue='LabelAutomation', durable=True)
    print(" [*] Waiting for order. To exit press CTRL+C")

    try:
        while True:
            for zip_file in os.listdir(new_order_dir):
                base_name_of_zip = os.path.splitext(zip_file)[0]
                shutil.move(os.path.join(new_order_dir, zip_file), os.path.join(order_processing_dir, zip_file))
                message = {
                    "service": "artwork_customer_approval",
                    "order": base_name_of_zip
                }
                channel.basic_publish(
                    exchange='',
                    routing_key='LabelAutomation',
                    body=json.dumps(message),
                    properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent)
                )
                print("Order sent for processing:", base_name_of_zip)
            time.sleep(5)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        connection.close()

if __name__ == "__main__":
    main()