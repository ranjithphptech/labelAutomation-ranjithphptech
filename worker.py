import pika
import multiprocessing
import signal
import os

processes = []  # Global list to store worker processes

def process_message(ch, method, properties, body):
    print(f"Received: {body.decode()}")
    ch.basic_ack(delivery_tag=method.delivery_tag)

def worker_function():
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        channel = connection.channel()
        channel.queue_declare(queue='task_queue', durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue='task_queue', on_message_callback=process_message)
        channel.start_consuming()
    except Exception as e:
        print(f"Worker encountered an error: {e}")

def start_workers():
    global processes
    num_workers = multiprocessing.cpu_count()
    processes = []
    for _ in range(num_workers):
        p = multiprocessing.Process(target=worker_function)
        processes.append(p)
        p.start()
    print(f"Started {num_workers} worker processes.")

def check_workers():
    global processes
    alive_processes = []
    for p in processes:
        if p.is_alive():
            alive_processes.append(p)
    processes = alive_processes

    if len(processes) < multiprocessing.cpu_count():
        print("Some worker processes are not running. Restarting...")
        start_workers()
    else:
        print(f"{len(processes)} worker processes are running.")

def stop_workers():
    global processes
    for p in processes:
        if p.is_alive():
            p.terminate() #send terminate signal
            p.join() #wait for process to stop.
    processes.clear() #clear the process list.
    print("All worker processes stopped.")

# if __name__ == "__main__": #! for testing purposes only
#     start_workers()