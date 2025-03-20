import pika
import json
import labelAutomationNew

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost', heartbeat=1800))
    channel = connection.channel()

    channel.queue_declare(queue='LabelAutomation', durable=True)

    def callback(ch, method, properties, body):
        try:
            j = json.loads(body)
            print(f"Order received for processing {j['order']}")
            labelAutomationNew.genProcess(processName='customer_order_approval', zipFile=j['order'])
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"Error processing order {j['order']}: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        finally:
            print(' [*] Waiting for order. To exit press CTRL+C')

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='LabelAutomation', on_message_callback=callback)

    print(' [*] Waiting for order. To exit press CTRL+C')
    channel.start_consuming()

if __name__ == "__main__":
    main()