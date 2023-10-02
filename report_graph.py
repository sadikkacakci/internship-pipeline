import sys
import os
sys.path.insert(0,os.getcwd())
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import warnings
warnings.filterwarnings("ignore")
from matplotlib.patches import Rectangle
import logging

logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] [%(levelname)s] %(message)s', 
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.getcwd()+"/logs")], 
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger(__name__)

# Get the directory of the currently executing script
script_dir = os.path.dirname(os.path.abspath(__file__))


def createFolder(path):
    os.makedirs(path)
    logger.info("folder is created: %s",path)


'''
    The `PlotGraph` class is responsible for plotting and saving sensor graphs, including outlier graphs.
'''
class PlotGraph:
    def __init__(self,total_df):
        self.all_data = total_df
        self.outliers_list = self.all_data.loc[self.all_data["Comment"] != "Normal"]["Sensor ID"].unique()
        self.outlier_graphs_path = []
        # self.trial = fixTrial(trial)
    def plotGraphs(self,trial):
        '''
            Plots and saves graphs for all active sensors according to the provided `trial` information. 
            The graphs display the situation of all active sensors with each feature plotted separately.
        '''
        all_data = self.all_data
        data = all_data.loc[all_data["trial_date"] == trial]
        sensor_list = data["Sensor ID"].unique().tolist()
        today = datetime.today().date()
        y_lim_value = 1
        feature_list = ["co2","o2","temp"]
        for feature in feature_list:
            plt.figure(figsize=(15, 6))   # figsize=(12, 6)          
            date_format = mdates.DateFormatter('%Y-%m-%d')
            plt.gca().xaxis.set_major_formatter(date_format)
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.gcf().autofmt_xdate()  
            plt.ylim(data[feature].min() - y_lim_value, data[feature].max() + y_lim_value)
            ood_sensors = self.outliers_list
            for sensor in sensor_list:
                temp_df = data.loc[data["Sensor ID"] == sensor]
                temp_df["Date"] = pd.to_datetime(temp_df["Date"])
                temp_df = temp_df.sort_values("Date") 
                module_label = temp_df["Module"].values[0]
                # temp_df = temp_df.sort_values("Date")
                if sensor in ood_sensors:
                    plt.plot(temp_df["Date"].values, temp_df[feature].values,label = module_label )
                else:
                    plt.plot(temp_df["Date"].values, temp_df[feature].values, color = "gray",label = "Normal")
            handles, labels = plt.gca().get_legend_handles_labels()
            by_label = dict(zip(labels, handles))
            sorted_keys = sorted(by_label.keys(), key=lambda x: x != 'Normal')
            by_label = {key: by_label[key] for key in sorted_keys}
            n_col = int(len(sensor_list) / 15)
            if n_col < 4:
                n_col = 3
            plt.legend(by_label.values(), by_label.keys(), loc='upper center', bbox_to_anchor=(0.5, -0.2), fancybox=True, shadow=True,ncol= n_col ) # , orientation='horizontal')# bbox_to_anchor=(1, 1)
            plt.grid()
            ax2 = plt.gca().twinx()
            ax2.set_ylim(data[feature].min() - y_lim_value, data[feature].max() + y_lim_value)
            # plt.grid()
            graph_path = os.path.join(script_dir, 'report_files', 'graphs')
            if not os.path.exists(graph_path):
                createFolder(graph_path)            
            plt.savefig(f"{graph_path}/{today}_{trial}_{feature}_graph.png", bbox_inches='tight')

    def getMinMaxNormalSensor(self,trial,feature):
        '''
            If available, returns the sensors that have the minimum and maximum values to provide guidelines. 
            This information is utilized in the `plotOutliers` function.
        '''
        min_row_sensor = 0
        max_row_sensor = 0
        if feature == "temp":
            return min_row_sensor,max_row_sensor
        temp_df2 = self.all_data.loc[self.all_data["trial_date"] == trial]
        temp_df3 = temp_df2.loc[temp_df2["Comment"] == "Normal"]
        if temp_df3.shape[0] == 0:
            return min_row_sensor,max_row_sensor
        min_value = temp_df3[feature].min()
        max_value = temp_df3[feature].max()
        min_row = temp_df3[temp_df3[feature] == min_value]
        max_row = temp_df3[temp_df3[feature] == max_value]
        min_row_sensor = min_row["Sensor ID"].values[0]
        max_row_sensor = max_row["Sensor ID"].values[0]
        return min_row_sensor,max_row_sensor
    
    def plotOutliers(self,trial):
        '''
            Plots and saves outlier graphs for all active sensors based on the provided `trial` information. 
            Each sensor's graph is plotted separately to highlight outlier data points.
        '''
        data = self.all_data.loc[self.all_data["trial_date"] == trial]
        # data = self.all_data
        sensor_list = data["Sensor ID"].unique()
        outlier_sensor_list = self.outliers_list
        today = datetime.today().date()
        feature_list = ["co2","o2","temp"]
        for sensor in sensor_list:
            plt.figure(figsize=(12, 6))   # figsize=(12, 6)          
            date_format = mdates.DateFormatter('%Y-%m-%d')
            plt.gca().xaxis.set_major_formatter(date_format)
            plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=1))
            plt.gcf().autofmt_xdate()  
            temp_df = data.loc[data["Sensor ID"] == sensor]
            temp_df = temp_df.sort_values("Date")
            title = f'{temp_df["Module"].values[0]} - {temp_df["Sensor ID"].values[0]}'
            plt.title(title)

            for feature in feature_list:
                min_row_sensor, max_row_sensor = self.getMinMaxNormalSensor(trial,feature)
                if ((min_row_sensor == 0) and (max_row_sensor == 0)):
                    plotGuideLines = False
                else:
                    min_sensor_df = self.all_data.loc[self.all_data["Sensor ID"] == min_row_sensor]
                    max_sensor_df = self.all_data.loc[self.all_data["Sensor ID"] == max_row_sensor]
                    if (min_sensor_df.shape[0] > 0 and max_sensor_df.shape[0] > 0):
                        min_sensor_df = min_sensor_df.sort_values("Date")
                        max_sensor_df = max_sensor_df.sort_values("Date")
                        plotGuideLines = True
                    else:
                        plotGuideLines = False
                if feature == "o2":
                    plt.plot(temp_df["Date"].values, temp_df[feature].values, color = "blue",label = "o2")
                    if plotGuideLines:
                        plt.plot(min_sensor_df["Date"].values, min_sensor_df[feature].values, color = "lightblue",label = "o2 guideline",linestyle='dashed')
                        plt.plot(max_sensor_df["Date"].values, max_sensor_df[feature].values, color = "lightblue",linestyle='dashed')
                elif feature == "co2":
                    plt.plot(temp_df["Date"].values, temp_df[feature].values, color = "red",label = "co2")
                    if plotGuideLines:
                        plt.plot(min_sensor_df["Date"].values, min_sensor_df[feature].values, color = "lightcoral",label = "co2 guideline",linestyle='dashed')
                        plt.plot(max_sensor_df["Date"].values, max_sensor_df[feature].values, color = "lightcoral",linestyle='dashed')
                elif feature == "temp":
                    plt.plot(temp_df["Date"].values, temp_df[feature].values, color = "orange",label = "temp")
                    # plt.plot(min_sensor_df["Date"].values, min_sensor_df[feature].values, color = "#FFA500",label = "min_temp",linestyle='dashed')
                    # plt.plot(max_sensor_df["Date"].values, max_sensor_df[feature].values, color = "#FFA500",label = "max_temp",linestyle='dashed')
            if sensor in outlier_sensor_list:
                x_min, x_max = plt.xlim()
                y_min, y_max = plt.ylim()
                rect_width =  (x_max - x_min) 
                rect_height = (y_max - y_min) 
                rect_x = x_min #x_min 
                rect_y = y_min #y_min 
                rect = Rectangle((rect_x, rect_y), rect_width, rect_height, linewidth=6, edgecolor='red', facecolor='none')
                plt.gca().add_patch(rect)
            graph_path = os.path.join(script_dir, 'report_files', 'outliers')
            if not os.path.exists(graph_path):
                createFolder(graph_path)       
            n_col = 3     
            plt.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), fancybox=True, shadow=True,ncol= n_col )
            plt.grid()
            path = f"{graph_path}/{today}_{sensor}_graph.png"
            plt.savefig(path, bbox_inches='tight')
            self.outlier_graphs_path.append(path)

    def getOutlierGraphPath(self):
        # Returns a list of paths to the outlier graphs that are generated by the `plotOutliers` function.
        return self.outlier_graphs_path