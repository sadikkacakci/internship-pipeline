import pandas as pd
from datetime import datetime
import sys
from new_customer import Customer2, getStorageDuration
from report import Report
from report import fixTrial
from mail import send_mail
import os
import logging
from amazons3 import S3
import pandas as pd
from forecaster import multiple_feature_forecasting
from sending_data import send_data_to_server, send_link
import time

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s', 
                    handlers=[logging.StreamHandler(sys.stdout),logging.FileHandler(os.getcwd()+"/logs") ], 
                    datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger(__name__)

script_dir = os.path.dirname(os.path.abspath(__file__))
today = datetime.today().date()

if __name__ == "__main__":
    # Initialize S3 connection
    s3 = S3()
    s3.initialize_s3()
    # Initialize customer manager
    customer_manager = Customer2()
    customer_manager.login()
    # Get a list of all customers
    all_customers = customer_manager.get_customers()
    # Initialize a report object
    report = Report()
    # Initialize DataFrames to store total data and metadata
    total_df = pd.DataFrame()
    total_meta = pd.DataFrame()
    files_to_delete = []
    freshsens_logo = s3.get_freshsens_logo()
    for temp_c in all_customers.keys():
        total_customer_df = pd.DataFrame()
        # Set the active customer for processing
        customer_manager.set_active_customer(temp_c)
        # Get a list of trials for the customer
        trials = customer_manager.get_trials()
        # Flag to create customer folders
        create_folders_bool = True
        # Check if there are trials for the customer
        if trials is None:
            logger.warning(f"No trial info for customer {temp_c}")
        else:
            # Initialize customer-specific folders in S3
            s3.initialize_basic_customer_folders(temp_c)
            # Get customer logo from S3
            customer_logo = s3.get_customer_logo(temp_c)
            logger.info(f"Starting pipeline for reporting for customer {temp_c}")
            logger.info(f"Trials {trials}")
            for trial in trials:
                # Parse trial date
                date_object = datetime.strptime(trial,"%d-%m-%Y")
                storage_duration = getStorageDuration(trial)
                customer_manager.init_trial(trial)
                fruit_type_list = customer_manager.get_fruit_type_list()
                for fruit_type in fruit_type_list:
                    # Flag to check if the trial is completed
                    trial_is_completed = False
                    # Check if trial data can be downloaded, else mark as completed
                    if not customer_manager.download_data_s3(temp_c, fruit_type, trial):
                        trial_is_completed = True
                    if trial_is_completed:
                        # Initialize folders for completed trials in S3
                        s3.initialize_completed_trials(temp_c,fruit_type,trial)
                        continue
                    customer_manager.preprocessing()
                    customer_manager.postprocessing(customer_manager.df)
                    customer_manager.outliers()
                    customer_df = customer_manager.all_data.copy(deep=True)
                    customer_df["trial_date"] = trial
                    customer_df["storage_duration"] = storage_duration
                    customer_df['Customer'] = customer_manager.active_customer
                    meta = customer_manager.meta.copy(deep = True)
                    try:
                        normal_sensors = meta.loc[meta["Comment"] == ""]["Sensor"].unique()
                        for sensor in normal_sensors:
                            condition = (meta["Sensor"] == sensor) & (meta["Customer"] == temp_c)
                            meta.loc[condition,"Comment"] = "Normal"
                    except Exception as err:
                        logger.info(f"No module for: {temp_c}")
                    meta["Comment"] = meta["Comment"].astype(str)
                    try:
                        for sensor in meta["Sensor"]:
                            temp = meta.loc[meta["Sensor"] == sensor]
                            values = temp.iloc[0]
                            condition = (customer_df["Sensor ID"] == int(sensor)) & (customer_df["Customer"] == meta["Customer"].values[0])
                            columns_to_update = ["Module", "Customer ID", "weight","Fruit Type", "Comment"]
                            customer_df.loc[condition, columns_to_update] = values[columns_to_update].values
                    except Exception as e:
                        logger.info(f"No module for customer {temp_c}")
                    # s3.initialize_detail_customer_folders(temp_c,fruit_type,trial)
                    customer_df_trial = customer_df.loc[customer_df["trial_date"] == trial]
                    meta_trial = meta.loc[meta["trial_date"] == trial]
                    customer_df_fruit_type = customer_df_trial.loc[customer_df_trial["Fruit Type"] == fruit_type]
                    meta_fruit_type = meta_trial.loc[meta_trial["Fruit Type"] == fruit_type]
                    total_customer_df = pd.concat([total_customer_df,customer_df_fruit_type])
                    if not trial_is_completed:
                        # Generate and upload trial reports to S3
                        trial_report = report.TrialReport(customer_df_fruit_type,meta_fruit_type,trial)
                        trial_report.report(customer_logo,freshsens_logo)
                        file_path = os.path.join(script_dir,"report_files","outputs",f"{temp_c}_{today}_trial_{fixTrial(trial)}_{fruit_type}_report.pdf")
                        target_folder = f"{temp_c}/trials/{fruit_type}-{trial}/reports/trial_reports"
                        file_name = f"{temp_c}_{today}_trial_{fixTrial(trial)}_{fruit_type}_report.pdf"
                        s3.upload_file_to_s3_v2(file_path,target_folder,file_name)
                        time.sleep(2)
                        ####
                        s3_path = target_folder + "/" + file_name
                        download_link = s3.get_download_link(s3_path)
                        customer_id = meta["Customer ID"].values[0]
                        send_link(customer_id,file_name,download_link)
                        ####
            try:
                # Generate and upload daily reports to S3
                for fruit_type in meta["Fruit Type"].unique():
                    customer_df_fruit_type = total_customer_df.loc[total_customer_df["Fruit Type"] == fruit_type]
                    meta_fruit_type = meta.loc[meta["Fruit Type"] == fruit_type]
                    daily_report = report.DailyReport(customer_df_fruit_type,meta_fruit_type)
                    daily_report.report(customer_logo,freshsens_logo)
                    file_path = os.path.join(script_dir,"report_files","outputs",f"{temp_c}_{today}_{fruit_type}_report.pdf")
                    target_folder = f"{temp_c}/daily_reports"
                    file_name = f"{temp_c}_{today}_{fruit_type}_report.pdf"
                    s3.upload_file_to_s3_v2(file_path,target_folder,file_name)
                    time.sleep(2)
                    ####
                    s3_path = target_folder + "/" + file_name
                    download_link = s3.get_download_link(s3_path)
                    customer_id = meta["Customer ID"].values[0]
                    send_link(customer_id,file_name,download_link)
                    ####
            except:
                pass
            # Concatenate data and metadata for the current customer
            total_df = pd.concat([total_df, total_customer_df])
            try:
                total_meta = pd.concat([total_meta, meta])
            except Exception as e:
                logging.error(f"There is no meta data for: {temp_c}")
    # Group data by module and create aggregated DataFrame
    send_data_bool = True

    if send_data_bool:
        test_df = total_df.groupby('Module')    
        newdf = [group_df.reset_index(drop=True) for _, group_df in test_df]
        agg_df = pd.DataFrame(columns=['Customer', 'Customer_id', 'Module', 'Sensor', 'Data', 'Forecasted Data'])
        agg_df['Data'] = newdf
        # Populate aggregated DataFrame
        for i, df in enumerate(newdf):
            agg_df.loc[i, 'Module'] = df['Module'].iloc[0]
            agg_df.loc[i, 'Sensor'] = df['Sensor ID'].iloc[0]
            agg_df.loc[i, 'Customer'] = df['Customer'].iloc[0]
            agg_df.loc[i, 'Customer_id'] = df['Customer ID'].iloc[0] 
        # Define forecasting parameters and perform multiple feature forecasting    
        for i in range(agg_df.shape[0]):
            data, train_window, forecasted_horizon, feature_list = agg_df.Data[i], 48, 24 , ['co2','o2', 'temp']
            forecasted = multiple_feature_forecasting(data, feature_list, train_window, forecasted_horizon)
            agg_df['Forecasted Data'][i] = forecasted
        # Send data to a server
        send_data_to_server(total_meta)
    
    send_mail_bool = True

    if send_mail_bool:
        receiver = "sadikkacakci90@gmail.com"
        script_dir = os.path.dirname(os.path.abspath(__file__))
        reports_directory = os.path.join(script_dir, 'report_files', 'outputs')
        file_list = os.listdir(reports_directory)
        file_path_list = []
        # Collect file paths for email attachments
        for file in file_list:
            file_with_path = reports_directory + "/" + file
            file_path_list.append(file_with_path)
            files_to_delete.append(file_with_path)
        # Send email with attachments
        send_mail(receiver,file_path_list)
        logger.info("Mail successfully sent!")

    # Delete Files
    delete_files_bool = True

    if delete_files_bool:
        logo_directory = os.path.join(script_dir, 'report_files', 'logo2')
        logo_list = os.listdir(logo_directory)
        # Delete generated files
        for logo in logo_list:
            logo_with_path = logo_directory + "/" + logo
            files_to_delete.append(logo_with_path)
        # Remove files
        for path in files_to_delete:
            os.remove(path)