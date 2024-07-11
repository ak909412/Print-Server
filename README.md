# Intermediary Print Server Using Raspberry Pi and Windows

## Project Overview
This project aims to develop a versatile print server system that can use either a Raspberry Pi or a Windows machine as intermediaries. This setup facilitates seamless printing from any device, regardless of direct compatibility with the printer. It leverages AWS for communication and Python scripts for efficient file handling and printer management, ensuring real-time feedback on printer status.

## Features
- **Seamless Printing**: Enables printing from any device using a centralized server.
- **Versatile Intermediary Options**: Both Raspberry Pi and Windows machines can be used as intermediaries.
- **AWS Integration**: Uses AWS services for file storage and communication.
- **Real-time Feedback**: Provides real-time status of active printers.
- **Efficient File Management**: Automated file handling and cleanup after printing.

## Hardware Requirements
- **Printer**
- **Raspberry Pi 4 Model B** or **Windows Machine**
- **End Devices** (computers, smartphones, etc.)

## Software Requirements
- **AWS**: For communication and API creation
- **CUPS (Common Unix Print System)**: For managing print jobs on Raspberry Pi
- **Python**: For scripting and automation
- **Postman**: For API testing

## Setup Instructions

### 1. Setting up AWS
1. **Create an S3 Bucket**: To store files to be printed.
2. **Create an API**: Use AWS API Gateway to create an API for uploading files to the S3 bucket.
3. **Configure AWS IoT Core**: For real-time feedback on printer status.

### 2. Setting up Raspberry Pi
1. **Install CUPS**: 
   ```sh
   sudo apt update
   sudo apt install cups
   sudo usermod -aG lpadmin pi
## Add Printer to CUPS: Access CUPS via https://<Raspberry Pi IP>:631 and add your printer.
## Python Script for Monitoring S3 Bucket:
Install required libraries:
sh
Copy code
pip install boto3 schedule
Create a Python script to monitor the S3 bucket, download files, and send print commands.

### 3. Setting up Windows Machine
#### Install Required Libraries:

pip install boto3 pywin32 AWSIoTPythonSDK schedule
#### Configure AWS CLI:

aws configure
## Python Script for Monitoring S3 Bucket:
Like the Raspberry Pi setup, create a Python script for handling print jobs.
### 4. Running the System
Start the Python Script: On either the Raspberry Pi or Windows machine to begin monitoring the S3 bucket.
Upload Files for Printing: Use the created API to upload files from any end device.
Monitor Print Jobs: The intermediary device will handle file downloads and print commands.
### 5. Feedback System
Active Printer Detection: The Python script will detect active printers and post the list to AWS IoT Core.
Access Printer Status: Use the API to get the list of currently active printers.
Testing
Using Postman: Test the API endpoints to ensure file upload and print commands work correctly.
Real Device Testing: Print from various end devices to verify seamless operation.
Contributions
Contributions are welcome! Please fork this repository and submit pull requests for any enhancements or bug fixes.

## License
This project is licensed under the MIT License.

## Contact
For any questions or support, don't hesitate to get in touch with Anurag Kumar at ak909412@gmail.com.
