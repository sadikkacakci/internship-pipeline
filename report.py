import sys
import os
sys.path.insert(0,os.getcwd())
import pandas as pd
from datetime import datetime
from reportlab.lib.utils import ImageReader
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from datetime import datetime
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter, landscape, A4
import warnings
from reportlab.lib.enums import TA_JUSTIFY
import re
warnings.filterwarnings("ignore")
from report_graph import PlotGraph
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

def fixTrial(date):
    current_format = "%d-%m-%Y"
    desired_format = "%Y-%m-%d"
    date_obj = datetime.strptime(date, current_format).date()
    new_date_string = date_obj.strftime(desired_format)
    return new_date_string

class Report:
    class TrialReport:
        def __init__(self,customer_data,customer_meta,trial):
            self.trial = fixTrial(trial)
            self.customer_data_trial, self.customer_meta_trial = self.setData(customer_data,customer_meta)
            self.customer_name = self.customer_data_trial["Customer"].values[0]
            self.trials_for_data_list = self.customer_data_trial["trial_date"].unique().tolist()
            self.all_sensors_length = self.customer_meta_trial.shape[0]
            self.all_active_sensors_length = len(self.customer_data_trial.loc[self.customer_data_trial["Comment"]!= "Completed"]["Sensor ID"].unique())
            self.outliers_list = self.customer_data_trial.loc[self.customer_data_trial["Comment"] != "Normal"]["Sensor ID"].unique()
            self.trial_data = None
            self.today = datetime.today().date()
            self.report_number = None
            # downloaded a font to write Turkish characters like ö,ş,ğ Docker_App/Report/Roboto
            pdfmetrics.registerFont(TTFont('Roboto-Regular', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Bold.ttf')))
            self.font_path = "Roboto/Roboto-Regular.ttf"
            self.bold_font_path = "Roboto/Roboto-Bold.ttf"
            self.font = "Roboto-Regular"
            self.bold_font = "Roboto-Bold"
            self.fruit_type = self.customer_meta_trial["Fruit Type"].values[0]
            self.kilogram = None
            self.module_number = None
            self.degree = 1
            self.page_count = 1
            self.all_sensors = 0
            self.all_active_sensors = 0
            self.outlier_graphs_path = []

        def setData(self,customer_data,customer_meta):
            # Sets and returns the customer_data and and metadata for the report.
            def extract_numbers_with_regex(input_string):
                # Provides to sort the data by module number.
                try:
                    return [int(num) for num in re.findall(r'\d+', input_string)]
                except:
                    return [0]
            customer_data["Date"] = pd.to_datetime(customer_data["Date"])
            customer_data["trial_date"] = pd.to_datetime(customer_data["trial_date"])
            customer_data['trial_date'] = customer_data['trial_date'].dt.strftime('%Y-%m-%d')
            customer_data["Sensor ID"] = customer_data["Sensor ID"].astype(int)
            customer_data["ModuleNumber"] = None
            for module_label in customer_data["Module"].unique():
                customer_data.loc[customer_data["Module"] == module_label,"ModuleNumber"] = extract_numbers_with_regex(module_label)[0]
            customer_data = customer_data.sort_values(by='ModuleNumber', ascending=True)
            customer_data = customer_data.reset_index(drop=True)
            customer_data.drop("ModuleNumber",axis = 1,inplace = True)
            customer_meta["Sensor"] = customer_meta["Sensor"].astype(int)

            customer_meta["trial_date"] = pd.to_datetime(customer_meta["trial_date"])
            customer_meta['trial_date'] = customer_meta['trial_date'].dt.strftime('%Y-%m-%d')
            
            customer_data_trial = customer_data.loc[customer_data["trial_date"] == self.trial]
            customer_meta_trial = customer_meta.loc[customer_meta["trial_date"] == self.trial]
            return customer_data_trial,customer_meta_trial

        def initializeCanvas(self):    
            # Initializes the canvas and creates a folder to save the report if the folder doesn't exist.   
            filename_path = os.path.join(script_dir, 'report_files', 'outputs')  
            if not os.path.exists(filename_path):
                createFolder(filename_path)
            self.filename = f"{filename_path}/{self.customer_name}_{self.today}_trial_{self.trial}_{self.fruit_type}_report.pdf"
            self.canvas = canvas.Canvas(self.filename, pagesize=letter)

        def initializeFreshsensLogo(self,freshsens_logo):
            # Places the Freshsens logo on the report.
            # logo size
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            # logo coordinates
            logo_x = 470
            logo_y = 700 # Docker_App/Report/report/logo
            logo_path = freshsens_logo
            logo = ImageReader(logo_path)
            self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)

        def initializeCustomerLogo(self,logo):
            # Places the Customer logo.
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            logo_x = 30 # 450
            logo_y = 700
            #######
            if logo == None:
                logger.warning(f"Logo doesn't exist for {self.customer_name}")
                return
            #####
            else:
                try:
                    logo_path = logo
                    logo = ImageReader(logo_path)
                    self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)
                except:
                    pass

        def initializeInformation(self):
            # Displays customer and report information below the customer's logo.
            self.canvas.setFont(self.font, 12)
            date_text = f"Date: {self.today}"
            report_number_text = f"Report Number: {self.report_number}" # today - trial date
            customer_text = f"Customer: {self.customer_name}"
            fruit_type_text = f"Fruit Type: {self.fruit_type}"
            date_x = 80
            date_y = 630 + 40
            report_number_x = 80
            report_number_y = 615 +40
            customer_x = 80
            customer_y = 600 +40
            fruit_type_x = 80
            fruit_type_y = 585 +40
            self.canvas.drawString(date_x, date_y, date_text)
            self.canvas.drawString(report_number_x, report_number_y, report_number_text)
            self.canvas.drawString(customer_x, customer_y, customer_text)
            self.canvas.drawString(fruit_type_x, fruit_type_y, fruit_type_text)
            self.addInfoTextVertical()

        def initializeBodyInformation(self,genel_text):
            '''
                Writes general information about sensors, including starting date, module count, and kilograms of fruit. 
                It also summarizes the current situation.
            '''
            self.canvas.setFont(self.font, 20)
            title_text = "Freshness Monitoring Report"
            title_x = 180
            title_y = 570
            self.canvas.drawString(title_x,title_y,title_text)
            self.canvas.setFont(self.font, 12)
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font 
            style.fontSize = 12
            style.alignment = TA_JUSTIFY
            genel_paragraph = Paragraph(genel_text, style)
            genel_paragraph.wrapOn(self.canvas, 450, 1000)  
            genel_paragraph.drawOn(self.canvas, 80, 500)

        def initializeBatchInformation(self):
            # Provides details about batches, including the total and active sensor count, and the total weight of active modules.
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font 
            style.fontSize = 12
            statistic_text = "Below is the detailed information regarding the ongoing batch:"
            statistic_x = 140
            statistic_y = 380
            self.canvas.drawString(statistic_x,statistic_y,statistic_text)
            data = [
                ["Type"," ", "Cherry"," "],
            ]
            data.append(["# Modules(Total)"," ",self.all_sensors_length, " "])
            data.append(["# Modules(Con.)"," ", self.all_active_sensors_length, " "])
            data.append(["Batch","Total","Active","Kilogram"])
            # self.trial_active_sensors
            trial_data = self.customer_meta_trial.loc[self.customer_meta_trial["trial_date"] == self.trial]
            trial_total_sensors_length = len(trial_data["Sensor"].unique())
            trial_active_sensors = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor"].unique()
            date_obj = datetime.strptime(self.trial, '%Y-%m-%d')
            month = date_obj.month
            day = date_obj.day
            date = f"{day}-{month}"
            kilogram = self.calculateWeight(trial_active_sensors)
            data.append([date,trial_total_sensors_length,len(trial_active_sensors),kilogram])
            table_style = (TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.font), 
                ('FONTSIZE', (0, 0), (-1, -1), 10), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                ('TOPPADDING', (0, 0), (-1, -1), 6), 
                ('LEFTPADDING', (0, 0), (-1, -1), 6),  
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),  
                ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0, 0.5)),  
                ('VALIGN', (0, 0), (-1, -1), 'TOP') #####
            ]))
            table = Table(data)
            table_style.add('SPAN', (0, 0), (1, 0)) # Combine columns 0 and 1 in row 0.
            table_style.add('SPAN', (2, 0), (3, 0)) 
            table_style.add('SPAN', (0, 1), (1, 1)) 
            table_style.add('SPAN', (2, 1), (3, 1))
            table_style.add('SPAN', (0, 2), (1, 2)) 
            table_style.add('SPAN', (2, 2), (3, 2)) 
            table_style.add('FONTNAME', (0, 0), (-1, 0), self.bold_font)
            table_style.add('FONTNAME', (0, 3), (-1, 3), self.bold_font)
            table_width = 200  
            num_cols = len(data[0])  
            col_width = table_width / num_cols

            table._argW = [col_width] * num_cols        
            table.setStyle(table_style)
    
            table_weight = 150 
            table_height = 100 
            table_x = 200
            table_y = 220       
            table.wrapOn(self.canvas, table_weight, table_height) 
            table.drawOn(self.canvas, table_x, table_y)

            self.canvas.setFont(self.bold_font,12)
            table_title = "Table 1:"
            table_text_x = 200
            table_text_y = table_y - 25
            self.canvas.drawString(table_text_x, table_text_y, table_title)
            table_text = "Overview of Batchs"
            self.canvas.setFont(self.font,12)
            self.canvas.drawString(250, table_text_y, table_text)    

        def addInfoTextVertical(self):
            # Provides to show vertical page information.
            page_count_x = 520
            page_count_y = 50
            self.canvas.setFont(self.font, 12)
            page_text = f"{self.page_count}"
            self.canvas.drawString(page_count_x,page_count_y,page_text)
            info_text = f"Freshness Monitoring Report #{self.report_number}"  
            info_text_x = 80
            info_text_y = 50
            self.canvas.drawString(info_text_x, info_text_y, info_text)
        
        def addInfoTextHorizontal(self):
            # Provides to show horizontal page information.
            page_text_x = 680
            page_text_y = 50   
            self.canvas.setFont(self.font, 12)
            page_text = f"{self.page_count}"
            self.canvas.drawString(page_text_x,page_text_y,page_text)
            info_text = f"Freshness Monitoring Report #{self.report_number}" # today - trial date      
            info_text_x = 80
            info_text_y = 50
            self.canvas.drawString(info_text_x, info_text_y, info_text) 

        def initializeSensorTable(self):
            '''
                Places a table displaying information about active sensors. 
                This includes Sensor ID, Module, most recent measurements, storage duration, and description.
            '''
            table_style = (TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                ('FONTNAME', (0, 0), (-1, -1), self.font),  
                ('FONTSIZE', (0, 0), (-1, -1), 10),  
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                ('TOPPADDING', (0, 0), (-1, -1), 6),  
                ('LEFTPADDING', (0, 0), (-1, -1), 6), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 6), 
                ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0, 0.5)), 
            ]))        
            table_style.add('FONTNAME', (0, 0), (-1, 0), self.bold_font)    

            self.canvas.showPage()
            page_width, page_height = A4
            self.canvas.setPageSize((page_width, page_height))
            self.page_count += 1
            self.addInfoTextVertical()
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font  
            style.fontSize = 12              
            outlier_text = "It is crucial to maintain close monitoring of these modules. The most recent measurements of the modules are as follows: "
            outlier_paragraph = Paragraph(outlier_text, style)
            outlier_paragraph.wrapOn(self.canvas, 500, 1000)
            outlier_paragraph.drawOn(self.canvas, 50, 750)

            data = [
                ["Module","Sensor ID","%O2","%CO2","°C","Weight","Storage_Duration","Description"],
            ] 
            def createTable2Df():
                # Creates a special df for table 2.
                def extract_numbers_with_regex(input_string):
                    return [int(num) for num in re.findall(r'\d+', input_string)]
                table2_df = pd.DataFrame()
                all_sensors = self.customer_data_trial["Sensor ID"].unique()
                for sensor in all_sensors:
                    temp_data = self.customer_data_trial.loc[self.customer_data_trial["Sensor ID"] == sensor]
                    temp_data = temp_data.sort_values("Date")
                    temp_sensor = temp_data.tail(1)
                    temp_sensor["Comment"] = self.customer_meta_trial.loc[self.customer_meta_trial["Sensor"] == int(sensor)]["Comment"]     
                    table2_df = pd.concat([table2_df,temp_sensor], ignore_index = True)
                table2_df["ModuleNumber"] = None
                for module_label in table2_df["Module"]:
                    table2_df.loc[table2_df["Module"] == module_label,"ModuleNumber"] = extract_numbers_with_regex(module_label)[0]
                table2_df = table2_df.sort_values(by='ModuleNumber', ascending=True)
                table2_df = table2_df.reset_index(drop=True)
                return table2_df
            
            df = createTable2Df()
            total_data = 0
            counter = 0
            length = df.shape[0]
            for i in range(df.shape[0]): 
                length -= 1
                test = df.iloc[i]
                temp = self.customer_data_trial.loc[self.customer_data_trial["Sensor ID"] == test["Sensor ID"]]
                description = temp["Comment"].values[0]
                if int(temp['storage_duration'].values[0]) == 1:
                    storage = f"{temp['storage_duration'].values[0]} day"
                else:
                    storage = f"{temp['storage_duration'].values[0]} days"
                weight = int(temp["weight"].values[0])
                if str(description).isnumeric():
                    description = f"OOD({description})" 
                    data.append([test["Module"],test["Sensor ID"],round(test["o2"],2),round(test["co2"],2),round(test["temp"],2),weight,storage,description])
                else:
                    data.append([test["Module"],test["Sensor ID"],round(test["o2"],2), round(test["co2"],2),round(test["temp"],2),weight,storage,description])
                if(len(data) % 25 == 0 and len(data) != 0): # if(i % 25 == 0 and i!= 0):
                    table = Table(data)
                    table.setStyle(table_style)
                    table_x = 50 #(250 * counter) # 80
                    table_y = 100 # 50
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1
                    counter += 1
                    data = [
                        ["Module","Sensor ID","%O2","%CO2","°C","Weight","Storage_Duration","Description"],
                    ]  
                    self.canvas.showPage()
                    page_width, page_height = A4
                    self.canvas.setPageSize((page_width, page_height))
                    self.page_count += 1
                    self.addInfoTextVertical()
                if(length < 25 and (i == df.shape[0] - 1)):
                    table_x = 50 # 50 + 100
                    table_y = 700 - 24*len(data) # 650
                    table = Table(data)
                    table.setStyle(table_style)
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1 

        def initializeGraphs(self):
            # Places O2, CO2, and temperature graphs on separate pages.
            graph_height = 400 / 1*1 # 300
            graph_width = 650 / 1*1 # 600
            graph_x = 70
            graph_y = 90
            title_x = 300
            title_y = 550 
            graph_path = os.path.join(script_dir, 'report_files', 'graphs')
            #O2
            o2_graph = f"{graph_path}/{self.today}_{self.trial}_o2_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            width, height = landscape(letter)
            self.canvas.setPageSize((width, height))
            o2_title = f"O2 Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, o2_title)
            self.canvas.drawImage(o2_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            #CO2
            co2_graph = f"{graph_path}/{self.today}_{self.trial}_co2_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            co2_title = f"CO2 Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, co2_title)
            self.canvas.drawImage(co2_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            #TEMP
            temp_graph = f"{graph_path}/{self.today}_{self.trial}_temp_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            temp_title = f"Temperature Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, temp_title)
            self.canvas.drawImage(temp_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            os.remove(f"{graph_path}/{self.today}_{self.trial}_co2_graph.png")
            os.remove(f"{graph_path}/{self.today}_{self.trial}_o2_graph.png")
            os.remove(f"{graph_path}/{self.today}_{self.trial}_temp_graph.png")

        def initializeOutliersGraphs(self):
            # Places graphs of active sensors, with 4 graphs per page. These graphs highlight outlier data points.
            graph_height = 250 # 300
            graph_width = 350 # 600
            self.canvas.showPage()
            self.page_count += 1
            width, height = landscape(letter)
            self.canvas.setPageSize((width, height))
            j = 0
            coordinate_index = 0
            length = len(self.outlier_graphs_path)
            for path in self.outlier_graphs_path:
                # graph_x = 30,416
                # graph_y = 100,400
                coordinates = [[30,350],[416,350],[30,70],[416,70]]
                graph_coordinate = coordinates[coordinate_index]
                graph_x = graph_coordinate[0]
                graph_y = graph_coordinate[1]
                self.canvas.drawImage(path, graph_x,graph_y , width=graph_width, height=graph_height)
                j += 1
                if(j % 4 == 0 and j!= 0):
                    self.canvas.showPage()
                    self.page_count += 1
                    width, height = landscape(letter)
                    self.canvas.setPageSize((width, height))
                length -= 1
                coordinate_index += 1
                if(length < 4 and coordinate_index == 4):
                    coordinate_index = 0
                if(coordinate_index == 4):
                    coordinate_index = 0
                os.remove(path)
                # print(f"{path} deleted.")
        def saveCanvas(self):
            # Saves the report.
            self.canvas.save()

        def getReportNumber(self):
            # Set Report Number
            trial_datetime = datetime.strptime(self.trial, "%Y-%m-%d").date()
            self.report_number = (self.today - trial_datetime).days 
            return self.report_number   
        
        def calculateWeight(self,sensor_list):
            active_weight = 0
            for sensor in sensor_list:
                weight = self.customer_meta_trial.loc[self.customer_meta_trial["Sensor"] == sensor]["weight"].values[0]
                active_weight += weight
            return active_weight
        
        def getGenelText(self):
            # Generates the general text to be displayed in `initializeBodyInformation`.
            def calculateTotalWeight():
                all_sensors = self.customer_meta_trial["Sensor"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_meta_trial.loc[self.customer_meta_trial["Sensor"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight
            def calculateActiveTotalWeight():
                all_sensors = self.customer_data_trial["Sensor ID"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_data_trial.loc[self.customer_data_trial["Sensor ID"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight    
            genel_text = f'This report has been exclusively prepared for our valued customer "{self.customer_name}". ' 
            # Set Genel Text
            trial_data = self.customer_meta_trial.loc[self.customer_meta_trial["trial_date"] == self.trial]
            trial_sensors_active = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor"].unique()
            trial_all_sensors_length = len(trial_data["Sensor"].unique())
            trial_sensors_active_length = len(trial_sensors_active)
            self.total_kilogram = calculateTotalWeight()
            self.active_total_kilogram = calculateActiveTotalWeight()
            kilogram = self.calculateWeight(trial_sensors_active)
            genel_text = genel_text + f"As of {self.trial}, a total of {trial_all_sensors_length} modules have been installed, with {trial_sensors_active_length} of them currently active, ensuring the preservation of {kilogram} kg of {self.fruit_type}. "  
                #DF SETTINGS    
            # genel_text = genel_text + f"In general, a total of {self.all_sensors_length} modules have been installed, with {self.all_active_sensors_length} of them currently active, ensuring the preservation of {self.active_total_kilogram} kg of {self.fruit_type}. "
            genel_text = genel_text + f"Please note that the expected nominal temperature inside the cold storage room is set at {self.degree}°C."
            return genel_text
        
        def report(self, logo,freshsens_logo):    
            # Executes all necessary functions in the class object and saves the complete report.
            plotGraph = PlotGraph(self.customer_data_trial) 
            self.getReportNumber()
            ### 
            genel_text = self.getGenelText()
            trial_data = self.customer_data_trial.loc[self.customer_data_trial["trial_date"] == self.trial]
            self.trial_active_sensors = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor ID"].unique()
            self.trial_total_sensors_length = len(trial_data["Sensor ID"].unique())
            self.trial_active_sensors_length = len(self.trial_active_sensors)
            logger.info(f"report number: %s",self.report_number)
            self.initializeCanvas()
            page_width, page_height = A4
            self.canvas.setPageSize((page_width, page_height))
            self.initializeFreshsensLogo(freshsens_logo)
            self.initializeCustomerLogo(logo=logo)
            self.initializeInformation() 
            self.initializeBodyInformation(genel_text)
            self.initializeBatchInformation()
            self.initializeSensorTable()
            plotGraph.plotGraphs(self.trial)
            self.initializeGraphs()
            plotGraph.plotOutliers(self.trial)
            self.outlier_graphs_path = plotGraph.outlier_graphs_path
            self.initializeOutliersGraphs()
            self.saveCanvas()
            logger.info(f"Successfully created!: {self.filename}")

    class DailyReport:
        def __init__(self,customer_data,customer_meta):
            self.customer_data, self.customer_meta = self.setData(customer_data,customer_meta)
            self.customer_name = self.customer_data["Customer"].values[0]
            self.trials = self.setTrials()
            self.all_sensors_length = self.customer_meta.shape[0]
            self.all_active_sensors_length = len(self.customer_data.loc[self.customer_data["Comment"]!= "Completed"]["Sensor ID"].unique())
            self.outliers_list = self.customer_data.loc[self.customer_data["Comment"] != "Normal"]["Sensor ID"].unique()
            self.trial = None
            self.trial_data = None
            self.today = datetime.today().date()
            self.report_number = None
            # downloaded a font to write Turkish characters like ö,ş,ğ Docker_App/Report/Roboto
            pdfmetrics.registerFont(TTFont('Roboto-Regular', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Bold.ttf')))
            self.font_path = "Roboto/Roboto-Regular.ttf"
            self.bold_font_path = "Roboto/Roboto-Bold.ttf"
            self.font = "Roboto-Regular"
            self.bold_font = "Roboto-Bold"
            self.fruit_type = self.customer_meta["Fruit Type"].values[0]
            self.kilogram = None
            self.module_number = None
            self.degree = 1
            self.page_count = 1
            self.all_sensors = 0
            self.all_active_sensors = 0
            self.outlier_graphs_path = []

        def setData(self,customer_data,customer_meta):
            # Sets and returns the customer_data and and metadata for the report.
            def extract_numbers_with_regex(input_string):
                # Provides to sort the data by module number.
                try:
                    return [int(num) for num in re.findall(r'\d+', input_string)]
                except:
                    return [0]
            customer_data["trial_date"] = pd.to_datetime(customer_data["trial_date"])
            customer_data['trial_date'] = customer_data['trial_date'].dt.strftime('%Y-%m-%d')
            customer_data["Date"] = pd.to_datetime(customer_data["Date"])
            customer_data["Sensor ID"] = customer_data["Sensor ID"].astype(int)
            customer_data["ModuleNumber"] = None
            for module_label in customer_data["Module"].unique():
                customer_data.loc[customer_data["Module"] == module_label,"ModuleNumber"] = extract_numbers_with_regex(module_label)[0]
            customer_data = customer_data.sort_values(by='ModuleNumber', ascending=True)
            customer_data = customer_data.reset_index(drop=True)
            customer_data.drop("ModuleNumber",axis = 1,inplace = True)

            customer_meta["trial_date"] = pd.to_datetime(customer_meta["trial_date"])
            customer_meta['trial_date'] = customer_meta['trial_date'].dt.strftime('%Y-%m-%d')
            customer_meta["Sensor"] = customer_meta["Sensor"].astype(int)
            return customer_data,customer_meta
        def setTrials(self):
            trials = self.customer_data["trial_date"].unique().tolist()
            datetime_trials = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in trials]
            # date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in self.trials]
            trials = sorted(datetime_trials)
            trials = [dt.strftime('%Y-%m-%d') for dt in trials]
            return trials

        def initializeCanvas(self):    
            # Initializes the canvas and creates a folder to save the report if the folder doesn't exist.     
            filename_path = os.path.join(script_dir, 'report_files', 'outputs')  
            if not os.path.exists(filename_path):
                createFolder(filename_path)
            self.filename = f"{filename_path}/{self.customer_name}_{self.today}_{self.fruit_type}_report.pdf"
            self.canvas = canvas.Canvas(self.filename, pagesize=letter)

        def initializeFreshsensLogo(self,freshsens_logo):
            # Places the Freshsens logo on the report.
            # logo size
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            # logo coordinates
            logo_x = 470
            logo_y = 700 # Docker_App/Report/report/logo
            # logo_path = os.path.join(script_dir, 'report_files', 'logo','freshsens_logov2.png')
            logo_path = freshsens_logo
            logo = ImageReader(logo_path)
            self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)

        def initializeCustomerLogo(self,logo):
            # Places the Customer logo.
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            logo_x = 30 # 450
            logo_y = 700
            if logo == None:
                logger.warning(f"Logo doesn't exist for {self.customer_name}")
                return
            else:
                try:
                    logo_path = logo
                    logo = ImageReader(logo_path)
                    self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)
                except:
                    pass

        def initializeInformation(self):
            # Displays customer and report information below the customer's logo.
            self.canvas.setFont(self.font, 12)
            date_text = f"Date: {self.today}"
            report_number_text = f"Report Number: {self.report_number}" # today - trial date
            customer_text = f"Customer: {self.customer_name}"
            fruit_type_text = f"Fruit Type: {self.fruit_type}"
            date_x = 80
            date_y = 630 + 40
            report_number_x = 80
            report_number_y = 615 +40
            customer_x = 80
            customer_y = 600 +40
            fruit_type_x = 80
            fruit_type_y = 585 +40
            self.canvas.drawString(date_x, date_y, date_text)
            self.canvas.drawString(report_number_x, report_number_y, report_number_text)
            self.canvas.drawString(customer_x, customer_y, customer_text)
            self.canvas.drawString(fruit_type_x, fruit_type_y, fruit_type_text)
            self.addInfoTextVertical()

        def initializeBodyInformation(self,genel_text):
            '''
                Writes general information about sensors, including starting date, module count, and kilograms of fruit. 
                It also summarizes the current situation.
            '''
            self.canvas.setFont(self.font, 20)
            title_text = "Freshness Monitoring Report"
            title_x = 180
            title_y = 570
            self.canvas.drawString(title_x,title_y,title_text)
            self.canvas.setFont(self.font, 12)
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font 
            style.fontSize = 12
            style.alignment = TA_JUSTIFY
            genel_paragraph = Paragraph(genel_text, style)
            genel_paragraph.wrapOn(self.canvas, 450, 1000)  
            genel_paragraph.drawOn(self.canvas, 80, 460)

        def initializeBatchInformation(self):
            # Provides details about batches, including the total and active sensor count, and the total weight of active modules.
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font 
            style.fontSize = 12
            statistic_text = "Below is the detailed information regarding the ongoing batch:"
            statistic_x = 140
            statistic_y = 380
            self.canvas.drawString(statistic_x,statistic_y,statistic_text)
            data = [
                ["Type"," ", "Cherry"," "],
            ]
            data.append(["# Modules(Total)"," ",self.all_sensors_length, " "])
            data.append(["# Modules(Con.)"," ", self.all_active_sensors_length, " "])
            data.append(["Batch","Total","Active","Kilogram"])
            # self.trial_active_sensors
            for trial in self.trials:
                trial_data = self.customer_meta.loc[self.customer_meta["trial_date"] == trial]
                trial_total_sensors_length = len(trial_data["Sensor"].unique())
                trial_active_sensors = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor"].unique()
                date_obj = datetime.strptime(trial, '%Y-%m-%d')
                month = date_obj.month
                day = date_obj.day
                date = f"{day}-{month}"
                kilogram = self.calculateWeight(trial_active_sensors)
                data.append([date,trial_total_sensors_length,len(trial_active_sensors),kilogram])
            table_style = (TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), self.font), 
                ('FONTSIZE', (0, 0), (-1, -1), 10), 
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                ('TOPPADDING', (0, 0), (-1, -1), 6), 
                ('LEFTPADDING', (0, 0), (-1, -1), 6),  
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),  
                ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0, 0.5)),  
                ('VALIGN', (0, 0), (-1, -1), 'TOP') #####
            ]))
            table = Table(data)
            table_style.add('SPAN', (0, 0), (1, 0)) # Combine columns 0 and 1 in row 0.
            table_style.add('SPAN', (2, 0), (3, 0)) 
            table_style.add('SPAN', (0, 1), (1, 1)) 
            table_style.add('SPAN', (2, 1), (3, 1))
            table_style.add('SPAN', (0, 2), (1, 2)) 
            table_style.add('SPAN', (2, 2), (3, 2)) 
            table_style.add('FONTNAME', (0, 0), (-1, 0), self.bold_font)
            table_style.add('FONTNAME', (0, 3), (-1, 3), self.bold_font)
            table_width = 200  
            num_cols = len(data[0])  
            col_width = table_width / num_cols

            table._argW = [col_width] * num_cols        
            table.setStyle(table_style)
    
            table_weight = 150 
            table_height = 100 
            table_x = 200
            table_y = 220       
            table.wrapOn(self.canvas, table_weight, table_height) 
            table.drawOn(self.canvas, table_x, table_y)

            self.canvas.setFont(self.bold_font,12)
            table_title = "Table 1:"
            table_text_x = 200
            table_text_y = table_y - 25
            self.canvas.drawString(table_text_x, table_text_y, table_title)
            table_text = "Overview of Batchs"
            self.canvas.setFont(self.font,12)
            self.canvas.drawString(250, table_text_y, table_text)    

        def addInfoTextVertical(self):
            # Provides to show vertical page information.
            page_count_x = 520
            page_count_y = 50
            self.canvas.setFont(self.font, 12)
            page_text = f"{self.page_count}"
            self.canvas.drawString(page_count_x,page_count_y,page_text)
            info_text = f"Freshness Monitoring Report #{self.report_number}"  
            info_text_x = 80
            info_text_y = 50
            self.canvas.drawString(info_text_x, info_text_y, info_text)
        
        def addInfoTextHorizontal(self):
            # Provides to show horizontal page information.
            page_text_x = 680
            page_text_y = 50   
            self.canvas.setFont(self.font, 12)
            page_text = f"{self.page_count}"
            self.canvas.drawString(page_text_x,page_text_y,page_text)
            info_text = f"Freshness Monitoring Report #{self.report_number}" # today - trial date      
            info_text_x = 80
            info_text_y = 50
            self.canvas.drawString(info_text_x, info_text_y, info_text) 

        def initializeSensorTable(self):
            '''
                Places a table displaying information about active sensors. 
                This includes Sensor ID, Module, most recent measurements, storage duration, and description.
            '''
            table_style = (TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                ('FONTNAME', (0, 0), (-1, -1), self.font),  
                ('FONTSIZE', (0, 0), (-1, -1), 10),  
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                ('TOPPADDING', (0, 0), (-1, -1), 6),  
                ('LEFTPADDING', (0, 0), (-1, -1), 6), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 6), 
                ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0, 0.5)), 
            ]))        
            table_style.add('FONTNAME', (0, 0), (-1, 0), self.bold_font)    

            self.canvas.showPage()
            page_width, page_height = A4
            self.canvas.setPageSize((page_width, page_height))
            self.page_count += 1
            self.addInfoTextVertical()
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font  
            style.fontSize = 12              
            outlier_text = "It is crucial to maintain close monitoring of these modules. The most recent measurements of the modules are as follows: "
            outlier_paragraph = Paragraph(outlier_text, style)
            outlier_paragraph.wrapOn(self.canvas, 500, 1000)
            outlier_paragraph.drawOn(self.canvas, 50, 750)

            data = [
                ["Module","Sensor ID","%O2","%CO2","°C","Weight","Storage_Duration","Description"],
            ] 
            def createTable2Df():
                def extract_numbers_with_regex(input_string):
                    return [int(num) for num in re.findall(r'\d+', input_string)]
                table2_df = pd.DataFrame()
                all_sensors = self.customer_data["Sensor ID"].unique()
                for sensor in all_sensors:
                    temp_data = self.customer_data.loc[self.customer_data["Sensor ID"] == sensor]
                    temp_data = temp_data.sort_values("Date")
                    temp_sensor = temp_data.tail(1)
                    temp_sensor["Comment"] = self.customer_meta.loc[self.customer_meta["Sensor"] == int(sensor)]["Comment"]     
                    table2_df = pd.concat([table2_df,temp_sensor], ignore_index = True)
                table2_df["ModuleNumber"] = None
                for module_label in table2_df["Module"]:
                    table2_df.loc[table2_df["Module"] == module_label,"ModuleNumber"] = extract_numbers_with_regex(module_label)[0]
                table2_df = table2_df.sort_values(by='ModuleNumber', ascending=True)
                table2_df = table2_df.reset_index(drop=True)
                return table2_df
            
            df = createTable2Df()
            total_data = 0
            counter = 0
            length = df.shape[0]
            for i in range(df.shape[0]): 
                length -= 1
                test = df.iloc[i]
                temp = self.customer_data.loc[self.customer_data["Sensor ID"] == test["Sensor ID"]]
                description = temp["Comment"].values[0]
                if int(temp['storage_duration'].values[0]) == 1:
                    storage = f"{temp['storage_duration'].values[0]} day"
                else:
                    storage = f"{temp['storage_duration'].values[0]} days"
                weight = int(temp["weight"].values[0])
                if str(description).isnumeric():
                    description = f"OOD({description})" 
                    data.append([test["Module"],test["Sensor ID"],round(test["o2"],2),round(test["co2"],2),round(test["temp"],2),weight,storage,description])
                else:
                    data.append([test["Module"],test["Sensor ID"],round(test["o2"],2), round(test["co2"],2),round(test["temp"],2),weight,storage,description])
                if(len(data) % 25 == 0 and len(data) != 0): # if(i % 25 == 0 and i!= 0):
                    table = Table(data)
                    table.setStyle(table_style)
                    table_x = 50 #(250 * counter)
                    table_y = 100 # 50
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1
                    counter += 1
                    data = [
                        ["Module","Sensor ID","%O2","%CO2","°C","Weight","Storage_Duration","Description"],
                    ] 
                    self.canvas.showPage()
                    page_width, page_height = A4
                    self.canvas.setPageSize((page_width, page_height))
                    self.page_count += 1
                    self.addInfoTextVertical()
                if(length < 25 and (i == df.shape[0] - 1)):
                    table_x = 50 # 50 + 100
                    table_y = 700 - 24*len(data) # 650
                    table = Table(data)
                    table.setStyle(table_style)
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1 

        def initializeGraphs(self):
            # Places O2, CO2, and temperature graphs on separate pages.
            graph_height = 400 / 1*1 # 300
            graph_width = 650 / 1*1 # 600
            graph_x = 70
            graph_y = 90
            title_x = 300
            title_y = 550 
            graph_path = os.path.join(script_dir, 'report_files', 'graphs')
            #O2
            o2_graph = f"{graph_path}/{self.today}_{self.trial}_o2_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            width, height = landscape(letter)
            self.canvas.setPageSize((width, height))
            o2_title = f"O2 Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, o2_title)
            self.canvas.drawImage(o2_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            #CO2
            co2_graph = f"{graph_path}/{self.today}_{self.trial}_co2_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            co2_title = f"CO2 Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, co2_title)
            self.canvas.drawImage(co2_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            #TEMP
            temp_graph = f"{graph_path}/{self.today}_{self.trial}_temp_graph.png"
            self.canvas.showPage()
            self.page_count += 1
            temp_title = f"Temperature Status {self.trial}"
            self.canvas.setFont(self.font, 20)
            self.canvas.drawString(title_x, title_y, temp_title)
            self.canvas.drawImage(temp_graph, graph_x,graph_y , width=graph_width, height=graph_height)
            self.addInfoTextHorizontal()
            os.remove(f"{graph_path}/{self.today}_{self.trial}_co2_graph.png")
            # print(f"{graph_path}/{self.today}_{self.trial}_co2_graph.png deleted")
            os.remove(f"{graph_path}/{self.today}_{self.trial}_o2_graph.png")
            # print(f"{graph_path}/{self.today}_{self.trial}_o2_graph.png deleted.")
            os.remove(f"{graph_path}/{self.today}_{self.trial}_temp_graph.png")
            # print(f"{graph_path}/{self.today}_{self.trial}_temp_graph.png deleted.")

        def initializeOutliersGraphs(self):
            # Places graphs of active sensors, with 4 graphs per page. These graphs highlight outlier data points.
            graph_height = 250 # 300
            graph_width = 350 # 600
            self.canvas.showPage()
            self.page_count += 1
            width, height = landscape(letter)
            self.canvas.setPageSize((width, height))
            j = 0
            coordinate_index = 0
            length = len(self.outlier_graphs_path)
            for path in self.outlier_graphs_path:
                # graph_x = 30,416
                # graph_y = 100,400
                coordinates = [[30,350],[416,350],[30,70],[416,70]]
                graph_coordinate = coordinates[coordinate_index]
                graph_x = graph_coordinate[0]
                graph_y = graph_coordinate[1]
                self.canvas.drawImage(path, graph_x,graph_y , width=graph_width, height=graph_height)
                j += 1
                if(j % 4 == 0 and j!= 0):
                    self.canvas.showPage()
                    self.page_count += 1
                    width, height = landscape(letter)
                    self.canvas.setPageSize((width, height))
                length -= 1
                coordinate_index += 1
                if(length < 4 and coordinate_index == 4):
                    coordinate_index = 0
                if(coordinate_index == 4):
                    coordinate_index = 0
                os.remove(path)
        def saveCanvas(self):
            # Saves the report.
            self.canvas.save()

        def getReportNumber(self):
            # Set Report Number
            datetime_trials = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in self.trials]
            min_datetime = min(datetime_trials).date()
            self.min_date = min_datetime
            self.report_number = (self.today - self.min_date).days 
            return self.report_number   
        
        def calculateWeight(self,sensor_list):
            active_weight = 0
            for sensor in sensor_list:
                weight = self.customer_meta.loc[self.customer_meta["Sensor"] == sensor]["weight"].values[0]
                active_weight += weight
            return active_weight
        
        def getGenelText(self):
            # Generates the general text to be displayed in `initializeBodyInformation`.
            def calculateTotalWeight():
                all_sensors = self.customer_meta["Sensor"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_meta.loc[self.customer_meta["Sensor"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight
            def calculateActiveTotalWeight():
                all_sensors = self.customer_data["Sensor ID"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_data.loc[self.customer_data["Sensor ID"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight    
            genel_text = f'This report has been exclusively prepared for our valued customer "{self.customer_name}". ' 
            for trial in self.trials:
                # self.trial = fixTrial(trial)
                # Set Genel Text
                trial_data = self.customer_meta.loc[self.customer_meta["trial_date"] == trial]
                trial_sensors_active = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor"].unique()
                trial_all_sensors_length = len(trial_data["Sensor"].unique())
                trial_sensors_active_length = len(trial_sensors_active)
                self.total_kilogram = calculateTotalWeight()
                self.active_total_kilogram = calculateActiveTotalWeight()
                kilogram = self.calculateWeight(trial_sensors_active)
                genel_text = genel_text + f"As of {trial}, a total of {trial_all_sensors_length} modules have been installed, with {trial_sensors_active_length} of them currently active, ensuring the preservation of {kilogram} kg of {self.fruit_type}. "  
                #DF SETTINGS    
            genel_text = genel_text + f"In general, a total of {self.all_sensors_length} modules have been installed, with {self.all_active_sensors_length} of them currently active, ensuring the preservation of {self.active_total_kilogram} kg of {self.fruit_type}. "
            genel_text = genel_text + f"Please note that the expected nominal temperature inside the cold storage room is set at {self.degree}°C."
            return genel_text
        
        def report(self, logo,freshsens_logo):    
            # Executes all necessary functions in the class object and saves the complete report.
            plotGraph = PlotGraph(self.customer_data) 
            self.getReportNumber()
            #SORT self.trials
            date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in self.trials]
            sorted_date_objects = sorted(date_objects)
            self.trials = [date.strftime("%Y-%m-%d") for date in sorted_date_objects]   
            ### 
            i = 0
            genel_text = self.getGenelText()
            if len(self.trials) > 1:
                for trial in self.trials:
                    self.trial = trial
                    trial_data = self.customer_data.loc[self.customer_data["trial_date"] == trial]
                    self.trial_active_sensors = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor ID"].unique()
                    self.trial_total_sensors_length = len(trial_data["Sensor ID"].unique())
                    self.trial_active_sensors_length = len(self.trial_active_sensors)
                    logger.info(f"report number: %s",self.report_number)
                    if i == 0:
                        self.initializeCanvas()
                        page_width, page_height = A4
                        self.canvas.setPageSize((page_width, page_height))
                        self.initializeFreshsensLogo(freshsens_logo)
                        self.initializeCustomerLogo(logo=logo)
                        self.initializeInformation() 
                        self.initializeBodyInformation(genel_text)
                        self.initializeBatchInformation()
                        self.initializeSensorTable()
                        # self.plotGraphs()
                        plotGraph.plotOutliers(trial) #######
                        plotGraph.plotGraphs(trial)
                        self.initializeGraphs()
                    else:
                        # self.plotGraphs()
                        plotGraph.plotGraphs(trial)
                        self.initializeGraphs()
                        # self.plotOutliers()
                        plotGraph.plotOutliers(trial)
                    i+=1
                self.outlier_graphs_path = plotGraph.outlier_graphs_path

                self.initializeOutliersGraphs()
            if(len(self.trials) == 1):
                trial = self.trials[0]
                self.trial_data = trial
                # self.trial = fixTrial(trial)
                self.trial = trial
                trial_data = self.customer_data.loc[self.customer_data["trial_date"] == trial]
                self.trial_active_sensors = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor ID"].unique()
                self.trial_total_sensors_length = len(trial_data["Sensor ID"].unique())
                self.trial_active_sensors_length = len(self.trial_active_sensors)
                logger.info(f"report number: %s",self.report_number)
                self.initializeCanvas()
                page_width, page_height = A4
                self.canvas.setPageSize((page_width, page_height))
                self.initializeFreshsensLogo(freshsens_logo)
                self.initializeCustomerLogo(logo=logo)
                self.initializeInformation() 
                self.initializeBodyInformation(genel_text)
                self.initializeBatchInformation()
                self.initializeSensorTable()
                # self.plotGraphs()
                plotGraph.plotGraphs(trial)
                self.initializeGraphs()
                # self.plotOutliers()
                plotGraph.plotOutliers(trial)
                self.outlier_graphs_path = plotGraph.outlier_graphs_path
                self.initializeOutliersGraphs()
            self.saveCanvas()
            logger.info(f"Successfully created!: {self.filename}")

    class WorkOrder:
        def __init__(self,customer_df,customer_meta,sales_order_df,count_opening_sensor,order_type): #sales_order,sales_order,count_opening_sensor
            self.customer_data,self.customer_meta,self.sales_order = self.setData(customer_df, customer_meta, sales_order_df)
            self.customer_meta = customer_meta
            self.count_opening_sensor = count_opening_sensor
            self.customer_name = self.sales_order["Customer"].values[0]
            self.trials = self.setTrials()
            self.opening_sensors_list = self.sales_order.head(self.count_opening_sensor)["Sensor"].tolist()
            self.customer_name = self.sales_order["Customer"].values[0]
            self.all_sensors_length = self.sales_order.shape[0]
            self.all_active_sensors_length = self.sales_order.loc[self.sales_order["Comment"] != "Completed"].shape[0]
            self.today = datetime.today().date()
            self.order_type = order_type
            self.degree = 1
            self.page_count = 1
            pdfmetrics.registerFont(TTFont('Roboto-Regular', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Regular.ttf')))
            pdfmetrics.registerFont(TTFont('Roboto-Bold', os.path.join(script_dir, 'report_files', 'font', 'Roboto-Bold.ttf')))
            self.font_path = "Roboto/Roboto-Regular.ttf"
            self.bold_font_path = "Roboto/Roboto-Bold.ttf"
            self.font = "Roboto-Regular"
            self.bold_font = "Roboto-Bold"
            self.fruit_type = "Cherry" #########################

        def setData(self,customer_data,customer_meta,sales_order_df):
            # Sets and returns the customer_data and and metadata for the report.
            customer_data["Date"] = pd.to_datetime(customer_data["Date"])
            customer_data["trial_date"] = pd.to_datetime(customer_data["trial_date"])
            customer_data['trial_date'] = customer_data['trial_date'].dt.strftime('%Y-%m-%d')
            customer_data["Sensor ID"] = customer_data["Sensor ID"].astype(int)

            customer_meta["Sensor"] = customer_meta["Sensor"].astype(int)
            customer_meta["trial_date"] = pd.to_datetime(customer_meta["trial_date"])
            customer_meta['trial_date'] = customer_meta['trial_date'].dt.strftime('%Y-%m-%d')
            
            sales_order_df["Sensor"] = sales_order_df["Sensor"].astype(int)
            return customer_data, customer_meta, sales_order_df
        
        def setTrials(self):
            trials = self.customer_data["trial_date"].unique().tolist()
            datetime_trials = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in trials]
            # date_objects = [datetime.strptime(date, "%Y-%m-%d") for date in self.trials]
            trials = sorted(datetime_trials)
            trials = [dt.strftime('%Y-%m-%d') for dt in trials]
            return trials
    
        def addInfoTextVertical(self):
            # Provides to show vertical page information.
            page_count_x = 520
            page_count_y = 50
            self.canvas.setFont(self.font, 12)
            page_text = f"{self.page_count}"
            self.canvas.drawString(page_count_x,page_count_y,page_text)

        def initializeCanvas(self):        
            # Initializes the canvas and creates a folder to save the report if the folder doesn't exist. 
            filename_path = os.path.join(script_dir, 'report_files', 'outputs')  
            if not os.path.exists(filename_path):
                createFolder(filename_path)
            if self.order_type == "lowo2":
                self.filename = f"{filename_path}/{self.customer_name}_{self.today}_{self.fruit_type}_work_order_report_lowo2.pdf"
            elif self.order_type == "problem":
                self.filename = f"{filename_path}/{self.customer_name}_{self.today}_{self.fruit_type}_work_order_report_problem.pdf"
            self.canvas = canvas.Canvas(self.filename, pagesize=letter)

        def initializeFreshsensLogo(self,freshsens_logo):
            # Places the Freshsens logo on the report.
            # logo size
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            # logo coordinates
            logo_x = 470
            logo_y = 700 # Docker_App/Report/report/logo
            # logo_path = os.path.join(script_dir, 'report_files', 'logo','freshsens_logov2.png')
            logo_path = freshsens_logo
            logo = ImageReader(logo_path)
            self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)

        def initializeCustomerLogo(self,logo):
            # Places the Customer logo.
            logo_width = 1.6 * inch
            logo_height = 1.6 * inch
            logo_x = 30 # 450
            logo_y = 700
            if logo == None:
                logger.warning("Logo doesn't exist for",self.customer_name)
                return
            else:
                try:
                    logo_path = logo
                    logo = ImageReader(logo_path)
                    self.canvas.drawImage(logo, logo_x, logo_y, width=logo_width, height=logo_height)
                except:
                    pass

        def initializeBodyInformation(self, genel_text):
            '''
                Writes general information about sensors, including starting date, module count, and kilograms of fruit. 
                It also summarizes the current situation.
            '''
            self.canvas.setFont(self.font, 20)
            title_text = "Customer Work Order"
            title_x = 200
            title_y = 650
            self.canvas.drawString(title_x,title_y,title_text)
            self.canvas.setFont(self.font, 12)
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font 
            style.fontSize = 12
            style.alignment = TA_JUSTIFY
            genel_paragraph = Paragraph(genel_text, style)
            genel_paragraph.wrapOn(self.canvas, 450, 1000)  
            genel_paragraph.drawOn(self.canvas, 80, 530)

            opened_sensors_information_text = f"Today, {len(self.opening_sensors_list)} modules will be opened up on request of the customer."
            opened_sensors_information_text_x = 80
            opened_sensors_information_text_y = 490
            self.canvas.drawString(opened_sensors_information_text_x,opened_sensors_information_text_y,opened_sensors_information_text)

        def initializeSensorTable(self):
            '''
                Places a table displaying information about active sensors. 
                This includes Sensor ID, Module, most recent measurements, storage duration, and description.
            '''
            table_style = (TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),  
                ('FONTNAME', (0, 0), (-1, -1), self.font),  
                ('FONTSIZE', (0, 0), (-1, -1), 10),  
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),  
                ('TOPPADDING', (0, 0), (-1, -1), 6),  
                ('LEFTPADDING', (0, 0), (-1, -1), 6), 
                ('RIGHTPADDING', (0, 0), (-1, -1), 6), 
                ('GRID', (0, 0), (-1, -1), 1, (0, 0, 0, 0.5)), 
            ]))        
            table_style.add('FONTNAME', (0, 0), (-1, 0), self.bold_font)    
            style = getSampleStyleSheet()["Normal"]
            style.fontName = self.font  
            style.fontSize = 12              
            outlier_text = "The descriptions of the modules are as follows: "
            outlier_text_x = 80
            outlier_text_y = 465
            self.canvas.drawString(outlier_text_x,outlier_text_y,outlier_text)

            data = [
                ["Module","Sensor ID","Storage Duration","Description"],
            ] 

            def createTable2Df():
                table2_df = pd.DataFrame()
                all_sensors = self.opening_sensors_list
                for sensor in all_sensors:
                    temp_data = self.sales_order.loc[self.sales_order["Sensor"] == sensor]
                    # temp_data = temp_data.sort_values("Date")
                    temp_sensor = temp_data.tail(1)
                    table2_df = pd.concat([table2_df,temp_sensor], ignore_index = True)
                return table2_df
            df = createTable2Df()
            total_data = 0
            counter = 0
            length = df.shape[0]
            first_page_table = True
            for i in range(df.shape[0]): 
                length -= 1
                test = df.iloc[i]
                # temp = self.sales_order.loc[self.sales_order["Sensor"] == test["Sensor"]]
                description = test["Comment"]
                storage = test["storage_duration"]
                if str(description).isnumeric():
                    description = f"OOD({description})" 
                    data.append([test["Module"],test["Sensor"],storage,description])
                else:
                    data.append([test["Module"],test["Sensor"],storage,description])

                if(len(data) == 17 and first_page_table):
                    table = Table(data)
                    table.setStyle(table_style)
                    table_x = 120 #(250 * counter)
                    table_y = (outlier_text_y - 10) - len(data)*24 # 50
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1
                    counter += 1
                    data = [
                        ["Module","Sensor ID","Storage Duration","Description"],
                    ]  
                    self.canvas.showPage()
                    page_width, page_height = A4
                    self.canvas.setPageSize((page_width, page_height))
                    self.page_count += 1
                    self.addInfoTextVertical()   
                    first_page_table = False    
                if(len(data) < 18 and (i == df.shape[0] - 1) and first_page_table):
                    table_x = 120 # 50 + 100
                    table_y = (outlier_text_y - 10) - 24*len(data) # 650
                    table = Table(data)
                    table.setStyle(table_style)
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1 
                    break
                if(len(data) % 28 == 0 and len(data) != 0): # if(i % 25 == 0 and i!= 0):
                    table = Table(data)
                    table.setStyle(table_style)
                    table_x = 120 #(250 * counter)
                    table_y = 100 # 50
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1
                    counter += 1
                    data = [
                        ["Module","Sensor ID","Storage_Duration","Description"],
                    ]  
                    self.canvas.showPage()
                    page_width, page_height = A4
                    self.canvas.setPageSize((page_width, page_height))
                    self.page_count += 1
                    self.addInfoTextVertical()
                if(length < 28 and (i == df.shape[0] - 1)):
                    table_x = 120 # 50 + 100
                    table_y = 772 - 24*len(data) # 650
                    table = Table(data)
                    table.setStyle(table_style)
                    table_weight = 100 
                    table_height = 100 
                    table.wrapOn(self.canvas, table_weight, table_height) 
                    table.drawOn(self.canvas, table_x, table_y) 
                    total_data += len(data) - 1 

        def saveCanvas(self):
            # Saves the report.
            self.canvas.save()

        def initializeOutliersGraphs(self):
            # Places graphs of active sensors, with 4 graphs per page. These graphs highlight outlier data points.
            graph_height = 250 # 300
            graph_width = 350 # 600
            self.canvas.showPage()
            self.page_count += 1
            width, height = landscape(letter)
            self.canvas.setPageSize((width, height))
            j = 0
            coordinate_index = 0
            length = len(self.outlier_graphs_path)
            for path in self.outlier_graphs_path:
                coordinates = [[30,350],[416,350],[30,70],[416,70]]
                graph_coordinate = coordinates[coordinate_index]
                graph_x = graph_coordinate[0]
                graph_y = graph_coordinate[1]
                self.canvas.drawImage(path, graph_x,graph_y , width=graph_width, height=graph_height)
                j += 1
                if(j % 4 == 0 and j!= 0):
                    self.canvas.showPage()
                    self.page_count += 1
                    width, height = landscape(letter)
                    self.canvas.setPageSize((width, height))
                length -= 1
                coordinate_index += 1
                if(length < 4 and coordinate_index == 4):
                    coordinate_index = 0
                if(coordinate_index == 4):
                    coordinate_index = 0
                os.remove(path)

        def calculateWeight(self,sensor_list):
            active_weight = 0
            for sensor in sensor_list:
                weight = self.customer_meta.loc[self.customer_meta["Sensor"] == sensor]["weight"].values[0]
                active_weight += weight
            return active_weight
        
        def getGenelText(self):
            # Generates the general text to be displayed in `initializeBodyInformation`.
            def calculateTotalWeight():
                all_sensors = self.customer_meta["Sensor"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_meta.loc[self.customer_meta["Sensor"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight
            def calculateActiveTotalWeight():
                all_sensors = self.customer_data["Sensor ID"].unique()
                total_weight = 0
                for sensor in all_sensors:
                    weight = self.customer_data.loc[self.customer_data["Sensor ID"] == sensor]["weight"].values[0]
                    total_weight += weight
                return total_weight    
            genel_text = f'This report has been exclusively prepared for our valued customer "{self.customer_name}". ' 
            for trial in self.trials:
                # self.trial = fixTrial(trial)
                # Set Genel Text
                trial_data = self.customer_meta.loc[self.customer_meta["trial_date"] == trial]
                trial_sensors_active = trial_data.loc[trial_data["Comment"]!= "Completed"]["Sensor"].unique()
                trial_all_sensors_length = len(trial_data["Sensor"].unique())
                trial_sensors_active_length = len(trial_sensors_active)
                self.total_kilogram = calculateTotalWeight()
                self.active_total_kilogram = calculateActiveTotalWeight()
                kilogram = self.calculateWeight(trial_sensors_active)
                genel_text = genel_text + f"As of {trial}, a total of {trial_all_sensors_length} modules have been installed, with {trial_sensors_active_length} of them currently active, ensuring the preservation of {kilogram} kg of {self.fruit_type}. "  
                #DF SETTINGS    
            genel_text = genel_text + f"In general, a total of {self.all_sensors_length} modules have been installed, with {self.all_active_sensors_length} of them currently active, ensuring the preservation of {self.active_total_kilogram} kg of {self.fruit_type}. "
            genel_text = genel_text + f"Please note that the expected nominal temperature inside the cold storage room is set at {self.degree}°C."
            return genel_text
                
        def report(self,logo,freshsens_logo):
            # Executes all necessary functions in the class object and saves the complete report.
            plotGraph = PlotGraph(self.customer_data) 
            self.initializeCanvas()
            page_width, page_height = A4
            self.canvas.setPageSize((page_width, page_height))
            self.initializeFreshsensLogo(freshsens_logo)
            self.initializeCustomerLogo(logo=logo)
            self.initializeBodyInformation(self.getGenelText())
            self.initializeSensorTable()
            for trial in self.customer_data["trial_date"].unique():
                plotGraph.plotOutliers(trial)

            self.outlier_graphs_path = plotGraph.outlier_graphs_path  
            self.initializeOutliersGraphs()
            self.saveCanvas()
            logger.info(f"Successfully created!: {self.filename}")