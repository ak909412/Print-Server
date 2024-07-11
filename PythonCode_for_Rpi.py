import boto3
import os
import time
import cups
import json
import subprocess
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# Configuration for AWS IoT Core
AWS_IOT_ENDPOINT = "a1z4x5kskjdqlv-ats.iot.us-east-1.amazonaws.com"  # Replace with your IoT endpoint
AWS_IOT_PORT = 8883
AWS_IOT_TOPIC = "feedback"  # Replace with your topic
AWS_IOT_STATUS_TOPIC = "status"  # Topic for status messages
AWS_IOT_CLIENT_ID = "Printer_feedback"  # Replace with your thing name
AWS_IOT_ROOT_CA = "/home/veris/Desktop/Printer/AWS IOT CREDS/AmazonRootCA1.pem"  # Replace with your CA certificate file path
AWS_IOT_PRIVATE_KEY = "/home/veris/Desktop/Printer/AWS IOT CREDS/private.key"  # Replace with your private key file path
AWS_IOT_CERTIFICATE = "/home/veris/Desktop/Printer/AWS IOT CREDS/9214b1e98f487158b870457828a4f615cf9d1c735b01f5d1d996780cde6b77ab-certificate.pem.crt"  # Replace with your client certificate file path

# Configuration for S3 and printers
BUCKETS = [
    {'name': 'file-storage-2', 'printer': 'Brother_DCP-T700W_'},
    {'name': 'printfile-storage', 'printer': 'Zebra_Technologies_ZTC_ZD421-300dpi_ZPL'}
]
REGION_NAME = 'us-east-1'
LOCAL_DOWNLOAD_PATH = '/home/veris/Desktop/Printer/temp'

def download_file_from_s3(s3_client, bucket_name, file_key, local_file_path):
    try:
        s3_client.download_file(bucket_name, file_key, local_file_path)
        print(f"Downloaded {file_key} from {bucket_name} to {local_file_path}")
    except Exception as e:
        print(f"Error downloading {file_key} from {bucket_name} to {local_file_path}: {str(e)}")
        return False
    return True

def print_file(file_path, printer_name):
    try:
        conn = cups.Connection()
        printers = conn.getPrinters()
        if printer_name not in printers:
            print(f"Printer {printer_name} not found")
            return False
        print(f"Printing to {printer_name}")
        conn.printFile(printer_name, file_path, "Python_Print_Job", {})
        return True
    except Exception as e:
        print(f"Error printing {file_path}: {str(e)}")
        return False

def process_bucket(s3_client, bucket_name, printer_name):
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in response:
            for obj in response['Contents']:
                file_key = obj['Key']
                if file_key.endswith('/'):  # Skip folders
                    continue
                file_name = os.path.basename(file_key)
                local_file_path = os.path.join(LOCAL_DOWNLOAD_PATH, file_name)
                download_success = download_file_from_s3(s3_client, bucket_name, file_key, local_file_path)
                if download_success:
                    print_success = print_file(local_file_path, printer_name)
                    if print_success:
                        # Delete the file from S3 after printing
                        s3_client.delete_object(Bucket=bucket_name, Key=file_key)
                        print(f"Deleted {file_key} from {bucket_name}")
                        # Remove local file
                        os.remove(local_file_path)
                    else:
                        print(f"Skipping {file_key} due to print error.")
        else:
            print(f'No new files in {bucket_name}.')
    except Exception as e:
        print(f"Error processing bucket {bucket_name}: {str(e)}")

def get_active_printers(printer_dict):
    conn = cups.Connection()
    printers = conn.getPrinters()
    active_printers = {}
    for printer_name in printer_dict.keys():
        if printer_name in printers and printers[printer_name]['printer-state'] == 3:
            active_printers[printer_name] = printer_dict[printer_name]
    return active_printers

def retrieve_print_logs():
    try:
        # Run lpstat command to fetch completed jobs
        completed_result = subprocess.run(['lpstat', '-W', 'completed', '-o'], capture_output=True, text=True, check=True)
        # Run lpstat command to fetch not-completed jobs
        not_completed_result = subprocess.run(['lpstat', '-W', 'not-completed', '-o'], capture_output=True, text=True, check=True)
        # Combine results
        combined_output = completed_result.stdout + not_completed_result.stdout
        # Split the output into lines
        lines = combined_output.strip().split('\n')
        job_logs = []
        # Process each line
        for line in lines:
            columns = line.split()
            if len(columns) >= 5:
                job_id = columns[0]
                owner = columns[1]
                job_size = columns[2]
                # Determine status by checking the presence of "completed"
                status = "completed" if job_id in completed_result.stdout else "not completed"
                timestamp = ' '.join(columns[3:])
                # Print job information with status
                job_logs.append({
                    "job_id": job_id,
                    "owner": owner,
                    "job_size": job_size,
                    "status": status,
                    "timestamp": timestamp
                })
            else:
                print(f"Issue parsing line: {line}")
        return job_logs
    except subprocess.CalledProcessError as e:
        print(f"Error retrieving print job logs: {e}")
        print(f"Command failed with return code {e.returncode}")
        print(f"Command output:\n{e.output}")
        return []

def send_to_aws_iot(message, topic):
    try:
        # Initialize AWS IoT MQTT Client
        mqtt_client = AWSIoTMQTTClient(AWS_IOT_CLIENT_ID)
        mqtt_client.configureEndpoint(AWS_IOT_ENDPOINT, AWS_IOT_PORT)
        mqtt_client.configureCredentials(AWS_IOT_ROOT_CA, AWS_IOT_PRIVATE_KEY, AWS_IOT_CERTIFICATE)
        # Connect and publish
        mqtt_client.connect()
        mqtt_client.publish(topic, json.dumps(message), 1)
        mqtt_client.disconnect()
        print("Message sent successfully.")
    except Exception as e:
        print(f"Failed to send message: {e}")

def main():
    s3_client = boto3.client('s3', region_name=REGION_NAME)
    # Input dictionary with specified printer names
    input_printers = {
        "Brother_DCP-T700W_": "File storage 2",
        "Brother_QL-720NW": "Home Printer",
        "Zebra_Technologies_ZTC_ZD421-300dpi_ZPL": "Print file storage"
    }
    while True:
        # Process S3 buckets and print files
        for bucket in BUCKETS:
            process_bucket(s3_client, bucket['name'], bucket['printer'])
        # Check active printers and send status to AWS IoT
        active_printers = get_active_printers(input_printers)
        if active_printers:
            for printer, description in active_printers.items():
                print(f"- {printer} is currently active")
            send_to_aws_iot({"active_printers": active_printers}, AWS_IOT_TOPIC)
        else:
            print("No active printers found.")
            send_to_aws_iot({"active_printers": "None"}, AWS_IOT_TOPIC)
        # Retrieve and send print logs
        print_logs = retrieve_print_logs()
        send_to_aws_iot({"print_logs": print_logs}, AWS_IOT_STATUS_TOPIC)
        time.sleep(5)

if __name__ == '__main__':
    if not os.path.exists(LOCAL_DOWNLOAD_PATH):
        os.makedirs(LOCAL_DOWNLOAD_PATH)
    main()
