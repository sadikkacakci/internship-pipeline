from amazons3 import S3
from report import Report
from filter import sales_sequence
from new_customer import getStorageDuration
import pandas as pd
import logging
import sys
import os
from datetime import datetime
import time
from sending_data import send_link

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s', 
                    handlers=[logging.StreamHandler(sys.stdout),logging.FileHandler(os.getcwd()+"/logs")],
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))


'''
    It calculates the count of opening sensors based on parameter weight,
    generates the work order report according to this and sends it to AWS.
'''

def create_work_order_report_v2(customer_name,weight,meta,fruit_type):
    files_to_delete = []
    # Initialize S3
    s3 = S3()
    s3.initialize_s3()
    # Get Logo
    freshsens_logo = s3.get_freshsens_logo()
    customer_logo = s3.get_customer_logo(customer_name)
    files_to_delete.append(freshsens_logo)
    files_to_delete.append(customer_logo)
    # Get ml.csv
    customer_df = pd.DataFrame()
    for trial in meta["trial_date"].unique():
        s3_path = f"{customer_name}/trials/{fruit_type}-{trial}/ml.csv"
        download_path = os.path.join(script_dir,f"ml-{trial}.csv")
        s3.download_file_from_s3_v2(s3_path,download_path)
        files_to_delete.append(download_path)
        ml_trial = pd.read_csv(download_path)
        ml_trial["trial_date"] = trial
        ml_trial["storage_duration"] = getStorageDuration(trial)
        ml_trial["Customer"] = customer_name
        ml_trial["Fruit Type"] = fruit_type
        customer_df = pd.concat([customer_df,ml_trial])
    for sensor in meta["Sensor"]:
        temp = meta.loc[meta["Sensor"] == sensor]
        values = temp.iloc[0]
        condition = (customer_df["Sensor ID"] == int(sensor)) & (customer_df["Customer"] == meta["Customer"].values[0])
        columns_to_update = ["Module", "Customer ID", "weight","Fruit Type", "Comment"]
        customer_df.loc[condition, columns_to_update] = values[columns_to_update].values
    def calculate_count_opening_sensor(weight,sales_order_df):
        collected_weight = 0
        count_opening_sensor = 0
        for index, row in sales_order_df.iterrows():
            weight_value = sales_order_df.loc[index,"weight"]
            collected_weight += weight_value
            count_opening_sensor += 1
            if(collected_weight > weight):
                return count_opening_sensor,collected_weight
    meta_fruit_type = meta.loc[meta["Fruit Type"] == fruit_type]
    customer_id = meta["Customer"].values[0]
    customer_df_fruit_type = customer_df.loc[customer_df["Fruit Type"] == fruit_type]
    # Generate Work Order
    report = Report()
    number_list = [0,1]
    for number in number_list:
        sales_order_df = sales_sequence(meta_fruit_type,number)
        count_opening_sensor,collected_weight = calculate_count_opening_sensor(weight,sales_order_df)
        if number == 0: #lowo2
            work_order = report.WorkOrder(customer_df_fruit_type,meta_fruit_type,sales_order_df,count_opening_sensor,"lowo2")
            work_order.report(customer_logo,freshsens_logo)
        if number == 1: #problem
            work_order = report.WorkOrder(customer_df_fruit_type,meta_fruit_type,sales_order_df,count_opening_sensor,"problem")
            work_order.report(customer_logo,freshsens_logo)
    # Send the reports to S3 AWS
    today = datetime.today().date()
    file_name_list = [f"{customer_name}_{today}_{fruit_type}_work_order_report_problem.pdf",f"{customer_name}_{today}_{fruit_type}_work_order_report_lowo2.pdf"]
    folder_path = f"{customer_name}/work_order_reports/"
    s3.create_folder_s3(folder_path)
    for file_name in file_name_list:
        file_path = os.path.join(script_dir,"report_files","outputs",file_name) 
        target_folder = f"{customer_name}/work_order_report"
        s3.upload_file_to_s3_v2(file_path, target_folder, file_name)
        time.sleep(2)
        s3_path = target_folder + "/" + file_name
        ####
        download_link = s3.get_download_link(s3_path)
        send_link(customer_id,file_name,download_link)
    ############
    files_to_delete.append(os.path.join(script_dir,"report_files","outputs",f"{customer_name}_{today}_{fruit_type}_work_order_report_problem.pdf"))
    files_to_delete.append(os.path.join(script_dir,"report_files","outputs",f"{customer_name}_{today}_{fruit_type}_work_order_report_lowo2.pdf"))
    # Delete the files.
    for path in files_to_delete:
        os.remove(path)