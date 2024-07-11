import schedule
import time
import json
import os
import boto3
import win32api
import win32print
from pathlib import Path
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from datetime import datetime  # Import datetime

# Configuration for AWS IoT Core
AWS_IOT_ENDPOINT = "a1z4x5kskjdqlv-ats.iot.us-east-1.amazonaws.com"
AWS_IOT_PORT = 8883
AWS_IOT_TOPIC_FEEDBACK = "feedback"
AWS_IOT_TOPIC_STATUS = "status"
AWS_IOT_CLIENT_ID = "Printer_feedback"
AWS_IOT_ROOT_CA = "X:/Desktop/Printer bridge/AWSIOTCREDS/AmazonRootCA1.pem"
AWS_IOT_PRIVATE_KEY = "X:/Desktop/Printer bridge/AWSIOTCREDS/private.key"
AWS_IOT_CERTIFICATE = "X:/Desktop/Printer bridge/AWSIOTCREDS/9214b1e98f487158b870457828a4f615cf9d1c735b01f5d1d996780cde6b77ab-certificate.pem.crt"

# Configuration for S3 and printers
BUCKETS = [
    {'name': 'file-storage-2', 'printer': 'Brother_DCP-T700W_Printer_(Copy_1)'},
    {'name': 'printfile-storage', 'printer': 'ZDesigner 105SLPlus-300dpi_ZPL'}
]
REGION_NAME = 'us-east-1'
LOCAL_DOWNLOAD_PATH = 'X:/Desktop/Printer bridge/temp'

# Initialize AWS S3 client
s3_client = boto3.client('s3', region_name=REGION_NAME)

def send_data_to_aws_iot(data, topic):
    try:
        # Initialize AWS IoT MQTT Client
        mqtt_client = AWSIoTMQTTClient(AWS_IOT_CLIENT_ID)
        mqtt_client.configureEndpoint(AWS_IOT_ENDPOINT, AWS_IOT_PORT)
        mqtt_client.configureCredentials(AWS_IOT_ROOT_CA, AWS_IOT_PRIVATE_KEY, AWS_IOT_CERTIFICATE)
        
        # Connect and publish
        mqtt_client.connect()
        mqtt_client.publish(topic, json.dumps(data), 1)
        mqtt_client.disconnect()
        print(f"Data sent successfully to {topic}.")
    except Exception as e:
        print(f"Failed to send data to AWS IoT: {e}")

def download_file_from_s3(bucket_name, file_key, local_file_path):
    try:
        s3_client.download_file(bucket_name, file_key, local_file_path)
        print(f"Downloaded {file_key} from {bucket_name} to {local_file_path}")
        return True
    except Exception as e:
        print(f"Error downloading {file_key} from {bucket_name} to {local_file_path}: {str(e)}")
        return False

def print_file(file_path, printer_name):
    try:
        win32api.ShellExecute(0, "print", file_path, None, ".", 0)
        print(f"Printing {file_path} to {printer_name}")
        return True
    except Exception as e:
        print(f"Error printing {file_path}: {str(e)}")
        return False

def delete_file_from_s3(bucket_name, file_key):
    try:
        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
        print(f"Deleted {file_key} from {bucket_name}")
    except Exception as e:
        print(f"Error deleting {file_key} from {bucket_name}: {str(e)}")

def list_active_printers():
    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

    printer_list = []
    for printer in printers:
        printer_name = printer[2]
        printer_handle = win32print.OpenPrinter(printer_name)
        try:
            status = win32print.GetPrinter(printer_handle, 2)["Status"]
            status_dict = {
                0: "Ready",
                1: "Paused",
                2: "Error",
                4: "Pending Deletion",
                8: "Paper Jam",
                16: "Paper Out",
                32: "Manual Feed",
                64: "Paper Problem",
                128: "Offline",
                256: "IO Active",
                512: "Busy",
                1024: "Printing",
                2048: "Output Bin Full",
                4096: "Not Available",
                8192: "Waiting",
                16384: "Processing",
                32768: "Initializing",
                65536: "Warming Up",
                131072: "Toner Low",
                262144: "No Toner",
                524288: "Page Punt",
                1048576: "User Intervention Required",
                2097152: "Out of Memory",
                4194304: "Door Open",
                8388608: "Server Unknown",
                16777216: "Power Save",
            }
            printer_status = status_dict.get(status, "Unknown")
        except Exception as e:
            printer_status = f"Unknown (Error: {e})"
        finally:
            win32print.ClosePrinter(printer_handle)
        
        printer_list.append((printer_name, printer_status))

    return printer_list

def get_job_status(job_status):
    status_dict = {
        0x00000000: "Printing",
        0x00000001: "Paused",
        0x00000002: "Error",
        0x00000004: "Deleting",
        0x00000008: "Spooling",
        0x00000010: "Printing",
        0x00000020: "Offline",
        0x00000040: "Paper Out",
        0x00000080: "Printed",
        0x00000100: "Deleted",
        0x00000200: "Blocked Device Queue",
        0x00000400: "User Intervention Required",
        0x00000800: "Restarted",
        0x00001000: "Complete",
        0x00002000: "Retained",
        0x00004000: "Rendering Locally",
    }
    return status_dict.get(job_status, "Unknown")

def list_print_jobs():
    print_jobs = []

    printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)

    for printer in printers:
        printer_name = printer[2]
        handle = win32print.OpenPrinter(printer_name)
        try:
            jobs = win32print.EnumJobs(handle, 0, -1, 1)
            for job in jobs:
                job_id = job['JobId']
                job_status = get_job_status(job['Status'])
                document = job['pDocument']
                submitted = job['Submitted']

                # Convert datetime to ISO format string
                if isinstance(submitted, datetime):
                    submitted = submitted.isoformat()

                print_jobs.append({
                    'Printer': printer_name,
                    'Job ID': job_id,
                    'Document': document,
                    'Submitted': submitted,
                    'Status': job_status,
                })
        except Exception as e:
            print(f"Error retrieving jobs for printer {printer_name}: {e}")
        finally:
            win32print.ClosePrinter(handle)
    
    return print_jobs

def process_bucket_and_print(bucket_name, printer_name):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                if file_key.endswith('/'):  # Skip folders
                    continue
                file_name = os.path.basename(file_key)
                local_file_path = os.path.join(LOCAL_DOWNLOAD_PATH, file_name)

                download_success = download_file_from_s3(bucket_name, file_key, local_file_path)
                if download_success:
                    print_success = print_file(local_file_path, printer_name)
                    if print_success:
                        delete_file_from_s3(bucket_name, file_key)
                        time.sleep(3)
                        os.remove(local_file_path)
                else:
                    print(f"Skipping {file_key} due to download error.")
        else:
            print(f'No new files in {bucket_name}.')
    except Exception as e:
        print(f"Error processing bucket {bucket_name}: {str(e)}")

def function1():
    try:
        printers_status = {
            'active_printers': list_active_printers(),
            'print_jobs': list_print_jobs()
        }
        send_data_to_aws_iot(printers_status, AWS_IOT_TOPIC_FEEDBACK)
    except Exception as e:
        print(f"Error in function1: {e}")

def function2():
    # Process S3 buckets and print files
    for bucket in BUCKETS:
        process_bucket_and_print(bucket['name'], bucket['printer'])

def function3():
    try:
        # Retrieve and send print job logs to AWS IoT
        print_jobs = list_print_jobs()
        
        # Convert print_jobs to JSON format
        json_data = json.dumps(print_jobs)  # Convert to JSON
        send_data_to_aws_iot(json_data, AWS_IOT_TOPIC_STATUS)
    except Exception as e:
        print(f"Error in function3: {e}")

def main():
    Path(LOCAL_DOWNLOAD_PATH).mkdir(parents=True, exist_ok=True)
    
    # Schedule tasks with different intervals
    schedule.every(3).seconds.do(function1)
    schedule.every(4).seconds.do(function2)
    schedule.every(0.5).seconds.do(function3)

    while True:
        schedule.run_pending()
        time.sleep(0.5)

if __name__ == "__main__":
    main()
