import pika
import json
import labelAutomationNew

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost',heartbeat=1800))
    channel = connection.channel()

    channel.queue_declare(queue='LabelAutomation')

    def callback(ch, method, properties, body):
        j = json.loads(body)
        print("order received for processing "+j['order'])
        labelAutomationNew.genProcess(processName='customer_order_approval',zipFile=j['order'])
        print(' [*] Waiting for order. To exit press CTRL+C')
                
    channel.basic_consume(queue='LabelAutomation', on_message_callback=callback, auto_ack=True)

    print(' [*] Waiting for order. To exit press CTRL+C')
    channel.start_consuming()

main()