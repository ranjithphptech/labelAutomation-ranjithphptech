import os
import shutil
import requests
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import Element,fromstring
from xml.etree.ElementTree import QName
import json
from svglib.svglib import svg2rlg
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle
from reportlab.lib.pagesizes import letter,A4
from reportlab.pdfgen import canvas
from reportlab.graphics import renderPDF
from reportlab.platypus import Image
from reportlab.pdfbase.pdfmetrics import stringWidth
import configparser
from datetime import datetime
import re
from db import conn
from helpers import *
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

PHP_API_URL = 'http://43.205.127.157/barcode_generator/barcode_millon_custom.php'
def genProcess(processName='',zipFile=''):
    print(zipFile)
    baseNameofZip = zipFile
    zipFile = zipFile+'.zip'
    config = configparser.ConfigParser()
    config.read('config.ini')
    orderProcessing = config['paths']['orderProcessing']
    orderOutputDir = config['paths']['orderOutputDir']
    svgDir = config['paths']['svgDir']
    customeApprovalPending = config['paths']['customeApprovalPending']
    failedOrders = config['paths']['failedOrders']
    currentOrderId = baseNameofZip
    try:
        print("process is going on "+zipFile)

        f = os.path.join(orderProcessing,zipFile)
        ordersData = {}
        with ZipFile(f,'r') as zObject:
             designCodes =[]
             currentZipOutputDir = orderOutputDir+"/"+baseNameofZip
             Path(currentZipOutputDir).mkdir(parents=True, exist_ok=True)
             zObject.extractall(currentZipOutputDir)
             
             for xmlFile in Path(currentZipOutputDir).rglob('*.xml'):
                XMLDir = os.path.splitext(xmlFile)[0]
                xmlFilename =  os.path.basename(xmlFile).split('/')[-1]
                print(xmlFilename)
                xmlFileBasename = os.path.splitext(xmlFilename)[0]
                designCodes.append(xmlFileBasename)
                Path(XMLDir).mkdir(parents=True, exist_ok=True)
                XMLtree = ET.parse(xmlFile)
                XMLRoot = XMLtree.getroot()                    
                orderID = XMLtree.find('OrderID').text
                customerID = XMLtree.find('CustomerID').text
                customerName = XMLtree.find('CustomerName').text
                customerEmail = XMLtree.find('CustomerEmail').text
                createdDate = XMLtree.find('CreatedDate').text
                all_sizes=[]
                ordersData[orderID] = {
                'customerID':customerID,
                'customerName':customerName,
                'customerEmail':customerEmail,
                'createdDate':createdDate,
                }
                assetNameList = XMLRoot.find("./OrderItems/OrderItem/Asset/Name").text.split(",")
                if len(assetNameList)==2:
                    assetName = assetNameList[1]
                else:
                    assetName = assetNameList[0]
            
                assetName = assetName.strip() 
                
                dbcursor = conn.cursor(dictionary=True)
                dbcursor.execute("SELECT * FROM label_list WHERE label_name = '"+assetName+".svg' ")
                labelDet = dbcursor.fetchone()
                dbcursor.close()
                dynamicLabel = 'no'
                print(labelDet['dynamic'])
                if labelDet['dynamic']=='1':
                    dynamicLabel = 'yes'
                if dynamicLabel=='yes':
                    frontAssetName = assetName+"_FRONT"
                    frontsvgString=svgDir+'/'+frontAssetName+'.svg'
                    namespaces = {node[0]: node[1] for _, node in ET.iterparse(frontsvgString, events=['start-ns'])}
                    for key, value in namespaces.items():
                        ET.register_namespace(key, value)
                    frontSVGtree = ET.parse(frontsvgString)
                    frontSVGtree.write(currentZipOutputDir+'/'+xmlFileBasename+'/1.svg')
                    
                svgString=svgDir+'/'+assetName+'.svg'
                namespaces = {node[0]: node[1] for _, node in ET.iterparse(svgString, events=['start-ns'])}
                for key, value in namespaces.items():
                    ET.register_namespace(key, value)
            
                items = XMLRoot.findall("./OrderItems/OrderItem/Item")
                if len(items)>1:
                    labelRatio = '0.3'
                else:
                    labelRatio = '0.5'
                
                supplierStype,country,color = '','',''
                for item in items:
                    SVGtree = ET.parse(svgString)
                    SVGroot = SVGtree.getroot()
                    itemID = item.find('./ItemID').text
                    qty = item.find('./Quantity').text  
                    set_svg_text(SVGroot, 'Quantity', qty)
                    Symbolname= ''               
                        
                    for size in item.findall("./SizeChartItem/Size"):
                        nameAttr = size.attrib['Name'].replace(' ', '_')
                        nameAttr = re.sub(r'[-_]+', '-', nameAttr).strip('-') 
                        if nameAttr=='ANNI-YEARS' or nameAttr=='MONTHS' or nameAttr=='YEARS':
                            if(nameAttr=='ANNI-YEARS' or nameAttr=='YEARS'):
                                    selected_size=size.attrib['Value']
                                    all_sizes = ["3-4", "4-5", "5-6", "6-7", "7-8","8-9","9-10"]  
                            set_svg_text(SVGroot, 'Age_Text', nameAttr)  
                            set_svg_text(SVGroot, 'Size_MONTHS_OR_YEAR', size.attrib['Value'])     
                            set_svg_text(SVGroot, 'ANNI-YEARS', size.attrib['Value'])
                            set_svg_text(SVGroot, 'YEARS', size.attrib['Value'])
                                
                    
                        elif nameAttr=='CM' :
                            set_svg_text(SVGroot, nameAttr, size.attrib['Value'])
                            set_svg_text(SVGroot, f'Size_{nameAttr}', size.attrib['Value'])
                            set_svg_text(SVGroot, 'Unit_Text', nameAttr)                       
                        
                        else:
                            set_svg_text(SVGroot, nameAttr, size.attrib['Value'])
                            if(nameAttr=='ITA'):
                                selected_size=size.attrib['Value']
                                all_sizes = ["S", "M", "L", "XL", "XXL"] 
                            if(nameAttr=='MESI-MONTHS'):
                                selected_size=size.attrib['Value']
                                all_sizes = ["0-1", "1-3", "3-6", "6-9"]  
                                            
                    
                    itemVariables = item.findall('./Variables/Variable')
                
                    Selling_price_X=''
                    for variable in itemVariables: 
                        
                        if variable.attrib['Question']=='Currency':
                            currency = variable.findall("./Answer/AnswerValues/AnswerValue")
                            for curr in currency:
                                currency_name = curr.attrib['Name']                            
                                if(currency_name=='Symbol'):
                                    Symbolname= curr.text 
                                    set_svg_text(SVGroot, 'CurrencySymbol', curr.text)                                   
                                                            
                            
                        if variable.attrib['Question']=='Selling Price':
                            answer_value_element = variable.find("./Answer/AnswerValues/AnswerValue")
                            if answer_value_element is not None and answer_value_element.text:
                                sellingPrice = answer_value_element.text.split(",")                        
                                selling_price_elements = SVGroot.findall(".//*[@id='Selling_Price']")                      
                                
                                for element in selling_price_elements:
                                    tag_name = element.tag.split('}')[-1]                           
                                    if tag_name == 'g': 
                                        Selling_price_X=sellingPrice[0]
                                        SVGroot.find(".//*[@id='Selling_Price']")[0].text = sellingPrice[0]
                                        if 0 <= 1 < len(sellingPrice):
                                            decimalPrice = sellingPrice[1]
                                        else:
                                            decimalPrice = "00"
                                        selling_price_2nd_half=","+decimalPrice
                                        print(f"Split Selling Price {selling_price_2nd_half}")
                                        SVGroot.find(".//*[@id='Selling_Price']")[1].text = selling_price_2nd_half
                                    elif tag_name == 'text':  
                                        print ("cursor Text")
                                        if len(sellingPrice) > 1:
                                            decimalPrice = sellingPrice[1] if len(sellingPrice) > 1 else "00"
                                            element.text = sellingPrice[0] + "," + decimalPrice
                                        else:
                                            print ("cursor Text else")
                                            element.text = sellingPrice
                            else:
                                sellingPrice = None
                                print("Warning: Selling Price is missing or empty.")
                    
                        if variable.attrib['Question']=='SKU Code':
                            skuCode = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                            set_svg_text(SVGroot, 'SKU_Code', skuCode)
                        
                        if variable.attrib['Question']=='OVS - MAN or WOMAN':
                            humanSize = variable.find("./Answer/AnswerValues/AnswerValue").text
                            set_svg_text(SVGroot, 'Human_Size', humanSize)
                                                    
                        if variable.attrib['Question']=='Commercial Ref':
                            commRef = variable.find("./Answer/AnswerValues/AnswerValue").text
                            set_svg_text(SVGroot, 'Commercial_Ref', commRef)
                            
                        if variable.attrib['Question']=='Country':
                            country = variable.find("./Answer/AnswerValues/AnswerValue").text
                        
                        if variable.attrib['Question']=='Color':
                            color = variable.find("./Answer/AnswerValues/AnswerValue").text
                            
                        if variable.attrib['Question']=='Style Code':
                            styleCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                            set_svg_text(SVGroot, 'Style_Code', styleCode)
                        
                        if variable.attrib['Question']=='Supplier Style':
                            supplierStype = variable.find("./Answer/AnswerValues/AnswerValue").text              
                    
                        if variable.attrib['Question']=='Translation Code':
                            translations = variable.findall("./Answer/AnswerValues/AnswerValue")
                            for translation in translations:
                                lang = translation.attrib['Name']                      
                                set_svg_text(SVGroot, f'Translation_Code_{lang}', translation.text)
                        if variable.attrib['Question']=='Material Type':
                            translations = variable.findall("./Answer/AnswerValues/AnswerValue")
                            for translation in translations:
                                lang = translation.attrib['Name']                      
                                set_svg_text(SVGroot, f'Material_Type_{lang}', translation.text)
                            
                            
                        
                        if variable.attrib['Question']=='Apparel Categories':
                            ApparelCategory = variable.find("./Answer/AnswerValues/AnswerValue").text                      
                            set_svg_text(SVGroot, 'Apparel_Categories', ApparelCategory)
                        
                        
                        if variable.attrib['Question']=='Department':
                            department = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                            set_svg_text(SVGroot, 'Department', department)

                        if variable.attrib['Question']=='Sub Department':
                            subdepartment = variable.find("./Answer/AnswerValues/AnswerValue").text
                            set_svg_text(SVGroot, 'Sub_Department', subdepartment)
                            
                            

                        if variable.attrib['Question']=='Barcode Number':
                            barcodenumber = variable.find("./Answer/AnswerValues/AnswerValue").text
                            data=barcodenumber
                            bar1 = barcodenumber[0] 
                            bar2 = barcodenumber[1:7]
                            bar3 = barcodenumber[7:]

                            bar_values = {'bar1': bar1,'bar2': bar2,'bar3': bar3 }

                            for bar_id, bar_text in bar_values.items():
                                set_svg_text(SVGroot, f'{bar_id}', bar_text)
                                
                            
                    
                        SVG_NS = "http://www.w3.org/2000/svg"
                        for size in all_sizes:    
                            rect_elem = SVGroot.find(f".//{{{SVG_NS}}}rect[@id='box_{size}']")
                            text_elem_rect = SVGroot.find(f".//{{{SVG_NS}}}text[@id='variable_Size_box_{size}']")
                            text_elem = SVGroot.find(f".//{{{SVG_NS}}}text[@id='variable_Size_{size}']")            

                            if size == selected_size:
                                
                                if rect_elem is not None:
                                    rect_elem.set("style", "display:inline")  
                                if text_elem_rect is not None:
                                    text_elem_rect.set(QName(SVG_NS, "style"), "display:inline")
                            else:
                                if rect_elem is not None:
                                    rect_elem.set("style", "display:none")  
                                if text_elem_rect is not None:
                                    text_elem_rect.set(QName(SVG_NS, "style"), "display:none")

                            
                            
                            

                    svgfilepath=currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg'
                    SVGtree.write(currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg')
                    
                    adjust_currency_transform(svgfilepath, 'CurrencySymbol', Symbolname, Selling_price_X, svgfilepath,itemID)
                    set_translate_for_group(svgfilepath, 'Selling_Price_X', 'Selling_Price', svgfilepath,Selling_price_X)
                    barcode_append(labelDet['barcode_x_position'],labelDet['barcode_y_position'],labelDet['barcode_width'],data,svgfilepath)
                    
                isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                if isPDFOutputDir==False:
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                if dynamicLabel=='no':
                    #assetName - texfilename and pdf filename
                    title = assetName+" - "+orderID
                else:
                    #assetName - texfilename and pdf filename
                    title = supplierStype+" - "+country+" - "+color+" - "+orderID
                buyerTxt         = 'BUYER               : OVS'
                submittedDateTxt = 'SUBMITTED DATE  : '+createdDate
                
                latexFilePath = currentZipOutputDir+"/"+assetName+"_"+baseNameofZip+".tex"
                latexFile = Path(latexFilePath)
                latexFile.touch(exist_ok= True)
                clatexFile = open(latexFilePath,"w")
                clatexFile.write('\\documentclass{article}\n')
                clatexFile.write('\\usepackage{multirow,tabularx}\n')
                clatexFile.write('\\usepackage{graphicx}\n')
                clatexFile.write('\\usepackage[export]{adjustbox}\n')
                clatexFile.write('\\usepackage[inkscapelatex=false]{svg}\n')
                clatexFile.write('\\usepackage[a4paper,left=5mm,right=5mm,bottom=5mm]{geometry}\n')
                clatexFile.write('\\setlength{\\voffset}{-0.75in}\n')
                clatexFile.write('\\setlength{\\headsep}{5pt}\n')
                clatexFile.write('\\usepackage{layout}\n')
                clatexFile.write('\\usepackage{fontspec}\n')
                clatexFile.write('\\newcolumntype{Y}{>{\\centering\\arraybackslash}X}\n')
                clatexFile.write('\\renewcommand{\\arraystretch}{1.2}\n')
                clatexFile.write('\\graphicspath{ {'+currentZipOutputDir+'/'+xmlFileBasename+'} }\n')
                
                #clatexFile.write('\\setmainfont{Barlow}\n')
                clatexFile.write('\\setmainfont{Barlow}[Path=./Barlow/,Extension = .ttf,UprightFont=*-Regular,BoldFont=*-Bold,ItalicFont=*-Italic,BoldItalicFont=*-BoldItalic]\n')
                clatexFile.write('\\begin{document}\n')
                clatexFile.write('\\begin{table}\n')
                clatexFile.write('\\begin{tabularx}{1\\textwidth}{|*{7}{Y|}}\n')
                clatexFile.write('\\hline\n')
                clatexFile.write('    \\multirow{2}{=}{ \\begin{center} \\includegraphics[height=1.6cm,width=3.9cm]{Sainmarknewlogo} \\end{center} }\n')
                clatexFile.write('    &\\multicolumn{3}{|p{10cm}|}{BUYER : '+buyerTxt+'}  &\\multirow{2}{=}{  \\begin{center} ARTWORK\\\\ FOR\\\\ APPROVAL \\end{center}} \\\\ \n')
                clatexFile.write('\\cline{2-4}\n')
                clatexFile.write('    &\\multicolumn{3}{l|}{CUSTOMER : '+customerName+'} &\\\\ \n')
                clatexFile.write('\\cline{2-4}\n')
                clatexFile.write('    &\\multicolumn{3}{l|}{DESIGN CODE : '+assetName+'} &\\\\ \n')
                clatexFile.write('\\cline{2-4}\n')
                clatexFile.write('    &\\multicolumn{3}{l|}{SUBMITTED DATE : '+submittedDateTxt+'} &\\\\ \n')
                clatexFile.write('\\cline{2-4}\n')
                clatexFile.write('    &\\multicolumn{3}{l|}{} &\\\\  \n')
                clatexFile.write('\\hline\n')
                clatexFile.write('\\end{tabularx}\n')
                clatexFile.write('\\end{table}\n')

                clatexFile.write('\\begin{center}\n')
                clatexFile.write('\\color{red} \\Large\n')
                clatexFile.write('\\textbf{'+title+'}\n')
                clatexFile.write('\\end{center}\n')

                clatexFile.write('\\hfill\\break\n')

                clatexFile.write('\\centering\n')
                
                for svg in sorted(os.listdir(currentZipOutputDir+'/'+xmlFileBasename)):
                        if svg.endswith(".svg"):
                            baseNameSVG = os.path.splitext(svg)[0]
                            clatexFile.write('\\includesvg[width='+labelRatio+'\\linewidth, height='+labelRatio+'\\linewidth]{'+baseNameSVG+'} \n')
                    
                clatexFile.write('\\end{document}\n')
                clatexFile.close()   
                
                x = os.system('xelatex --shell-escape --enable-write18 --export-latex /home/ubuntu/labelAutomation/'+latexFilePath+' --output-directory=/home/ubuntu/labelAutomation/'+currentZipOutputDir+'/pdf/ ') 
                
                #print(ordersData)
                oid =''
                for x in ordersData:
                    oid = x
                
                submitted_date = datetime.strptime(ordersData.get(oid).get('createdDate'),'%d/%m/%Y %H:%M').date()
                toemail = ordersData.get(oid).get('customerEmail')
       
        dbcursor = conn.cursor()
        approval_mail_status = 'P'
        dbcursor.execute("INSERT INTO orders(order_id, buyer, customer_id,customer_name, customer_email_id,approval_mail_status, design_codes, submitted_date,status, created_date_time) VALUES('"+oid+"', 'OVS','"+ordersData.get(oid).get('customerID')+"', '"+ordersData.get(oid).get('customerName')+"', '"+ordersData.get(oid).get('customerEmail')+"','"+approval_mail_status+"', '"+(",".join(designCodes))+"', '"+str(submitted_date)+"', 'CAW', '"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"');")
        conn.commit()
        print('mail triggered')
        delete_folder_contents('/home/ubuntu/labelAutomation/svg-inkscape/')
        #res = send_mail(subject='Subject',toMailid='ranjith@indsys.holdings',attachmentPath=currentZipOutputDir+'/pdf')
        res = send_mail(subject='Subject',toMailid='ranjith@indsys.holdings',attachmentPath='/home/ubuntu/labelAutomation/')
        print(res['status'])
        if res['status']=='success':
             approval_mail_status = 'S'
             shutil.move(orderProcessing+'/'+baseNameofZip+'.zip', customeApprovalPending+'/'+baseNameofZip+'.zip')
        else:
            approval_mail_status = 'F'
            shutil.move(orderProcessing+'/'+baseNameofZip+'.zip', failedOrders+'/'+baseNameofZip+'.zip')
            dbcursor = conn.cursor()
            dbcursor.execute("INSERT INTO failed_orders(order_id,error,status,created_date_time) VALUES('"+currentOrderId+"','"+res['msg']+"','F','"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"')")
            conn.commit()
        
        dbcursor = conn.cursor()
        dbcursor.execute("UPDATE orders SET approval_mail_status='"+approval_mail_status+"' WHERE order_id='"+currentOrderId+"'")
        conn.commit()
        delete_folder_contents(currentZipOutputDir)
        path = os.path.join(orderOutputDir, baseNameofZip)
        os.rmdir(path)
       
    except Exception as error:
        print(error)       
        shutil.move(orderProcessing+'/'+baseNameofZip+'.zip', failedOrders+'/'+baseNameofZip+'.zip')       
        dbcursor = conn.cursor()
        dbcursor.execute("INSERT INTO failed_orders(order_id,error,status,created_date_time) VALUES('"+currentOrderId+"','"+str(format(error)).replace("'",'"').strip()+"','F','"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"')")
        conn.commit()

# genProcess('customer_order_approval','B0257348')
def process_barcode(data, x, y, width):
    if not data or x is None or y is None or width is None:
        return {"error": "Please provide data, x, y, and width parameters", "status_code": 400}
    
    payload = {
        'data': data,
        'x': x,
        'y': y,
        'width': width
    }

    try:
        # Replace PHP_API_URL with the actual URL of your PHP API
       
        response = requests.post(PHP_API_URL, data=payload)

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Failed to contact PHP API", "status_code": response.status_code}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request failed: {str(e)}", "status_code": 500}
    
def set_svg_text(svg_root, element_id, text_value):
    element = svg_root.find(f".//*[@id='{element_id}']")
    if element is not None:
        element.text = text_value
    else:
        print(f"ID '{element_id}' not found in SVG.")

def set_currency_visibility(SVGroot, currency_name):    
    for currency_elem in SVGroot.findall(".//*[@id]"):
        if currency_elem.attrib['id'].startswith('CurrencySymbol_'):
            if currency_elem.attrib['id'] == f'CurrencySymbol_{currency_name}':
                currency_elem.set('style', 'visibility: visible;')
            else:
                currency_elem.set('style', 'visibility: hidden;')


def adjust_currency_transform(file_path, currency_id, currency_symbol, selling_price, output_path,itemID):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', 'http://www.w3.org/2000/svg')  

    currency_element = root.find(f".//*[@id='{currency_id}']", namespaces=namespace)
    if currency_element is None:
        print(f"Currency symbol with id '{currency_id}' not found.")
        return

  
    current_transform = currency_element.attrib.get('transform', '')
    if 'translate(' not in current_transform:
        print(f"No valid translate transform found for currency symbol with id '{currency_id}'.")
        return

   
    try:
        translate_values = current_transform.replace('translate(', '').replace(')', '').strip().split()
        x = float(translate_values[0])
        y = float(translate_values[1]) if len(translate_values) > 1 else 0.0
    except ValueError:
        print(f"Invalid transform format for currency symbol: {current_transform}")
        return


    currency_length = len(currency_symbol)
    print(f"Currency Length :{currency_length},Item ID : {itemID}")
    selling_price_length = len(selling_price)


    if currency_length == 3:
        x -= 14  

    if selling_price_length == 3:
        x -= 5  
    elif selling_price_length == 4:
        x -= 10  

    new_transform = f"translate({x} {y})"
    currency_element.set('transform', new_transform)
    print(f"Updated transform for currency symbol to {new_transform}")


    tree.write(output_path)
    print(f"SVG has been updated and saved as '{output_path}'.")

def barcode_append(x, y, width, data, svgfile):
    print(f"Received data: {data}, x: {x}, y: {y}, width: {width}")
    
    # Read configuration
    config = configparser.ConfigParser()
    config.read('config.ini')
    svgDir = config['paths']['svgDir']
    assetName = 'TO100'
    svgPath = svgfile

    # Process barcode
    barcode_response = process_barcode(data, x, y, width)
   
    if isinstance(barcode_response, dict) and "error" in barcode_response:
        return {"error": barcode_response["error"], "status_code": barcode_response.get("status_code", 500)}

    if isinstance(barcode_response, list) and len(barcode_response) > 0:
        barcode_data = barcode_response[0]
        bars_content = barcode_data.get('barsContent')
        print (f"bars_content{bars_content}")
    else:
        print(f"Unexpected response format: {barcode_response}")
        return {"error": "Unexpected response format from PHP API", "status_code": 500}

    if not bars_content:
        return {"error": "No 'barsContent' returned from PHP API", "status_code": 500}

    # Modify the SVG
    try:
        tree = ET.parse(svgPath)
        root = tree.getroot()
        namespaces = {'ns0': 'http://www.w3.org/2000/svg'}
        bars_element = ET.fromstring(bars_content)
        target_rect = root.find(".//*[@id='barcode']", namespaces)
        
        if target_rect is not None:
            for elem in bars_element.iter():
                if '}' in elem.tag:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag.split('}')[1]}"
                else:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag}"
            target_rect.append(bars_element)
        else:
            print("No <rect> element found with id='barcode'.")
            return {"error": "No <rect> element found with id='barcode'.", "status_code": 404}

        # Write changes back to the SVG file
        tree.write(svgPath, encoding='utf-8', xml_declaration=True)
        return {"message": "SVG updated successfully", "output_path": svgPath}
    except ET.ParseError as e:
        return {"error": f"SVG parsing error: {str(e)}", "status_code": 500}

def set_translate_for_group(file_path, symbol_id_prefix, group_id, output_path, Selling_price_X):
    tree = ET.parse(file_path)
    root = tree.getroot()
    
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', 'http://www.w3.org/2000/svg')  


    symbol_elements = root.findall(f".//*[@id='{symbol_id_prefix}']", namespaces=namespace)
    if not symbol_elements:
        print(f"Elements with id prefix '{symbol_id_prefix}' not found.")
        return

    for elem in symbol_elements:
        print(f"ID: {elem.attrib.get('id')}, Transform: {elem.attrib.get('transform')}")

    group_element = root.find(f".//*[@id='{group_id}']", namespaces=namespace)
    if group_element is None:
        print(f"Group with id '{group_id}' not found.")
        return

 
    text_elements = group_element.findall(".//svg:text", namespaces=namespace)
    if not text_elements:
        print("No text elements found within the group.")
        return

  
    
    string_length = len(Selling_price_X) 
    translate_adjustment = 0
    translate_adjustment_decimal=0
    if string_length == 3:
        translate_adjustment = -3
        translate_adjustment_decimal=8
    elif string_length == 4:
        translate_adjustment = -6
        translate_adjustment_decimal=16

   
    for i, text_element in enumerate(text_elements):
        if i < len(symbol_elements):
            symbol_transform = symbol_elements[i].attrib.get('transform', '')
            if 'translate(' in symbol_transform:
              
                translate_values = symbol_transform.replace('translate(', '').replace(')', '').strip().split()
                try:
                    x = float(translate_values[0])
                    y = float(translate_values[1]) if len(translate_values) > 1 else 0.0

                   
                    if i == 0:
                        x -= translate_adjustment  
                    elif i == 1:
                        x += translate_adjustment_decimal  

                    
                    new_transform = f"translate({x} {y})"
                    text_element.set('transform', new_transform)
                    
                except (ValueError, IndexError):
                    print(f"Invalid transform format for symbol element {i+1}: {symbol_transform}")
            else:
                print(f"No valid translate transform found for symbol element {i+1}.")
        else:
            print(f"No corresponding symbol element for text element {i+1}")

 
    tree.write(output_path)

# while True:
#     files = [f for f in os.listdir('new_orders') if os.path.isfile(os.path.join('new_orders', f))]
#     if len(files)>0:
#         for file in files:
#             full_path = os.path.join('new_orders', file)
#             genProcess('customer_order_approval', os.path.splitext(file)[0])
#             if os.path.exists(full_path):
#                 os.remove(full_path)