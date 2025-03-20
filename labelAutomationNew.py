import os
import shutil
from db import conn
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from pathlib import Path
import configparser
from datetime import datetime
import re
from helpers import *
import ean13barcode as bc
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from fpdf import FPDF
from lxml import etree
import code128 as c128bc

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
mandatoryIds=[]
def genProcess(processName='',zipFile=''):
    baseNameOfZip = zipFile
    zipFile = zipFile+'.zip'
    config = configparser.ConfigParser()
    config.read('config.ini')
    orderProcessing = config['paths']['orderProcessing']
    orderOutputDir = config['paths']['orderOutputDir']
    svgDir = os.path.join('static',config['paths']['svgDir'])
    customerApprovalPending =  config['paths']['customerApprovalPending']
    failedOrders = config['paths']['failedOrders']
   
    if not os.path.exists(os.path.join(orderProcessing,zipFile)):
        if os.path.exists(os.path.join(failedOrders,zipFile)):
            shutil.move(os.path.join(failedOrders,zipFile),orderProcessing)
        if os.path.exists(os.path.join(customerApprovalPending,zipFile)):
            shutil.move(os.path.join(customerApprovalPending,zipFile),orderProcessing)
        
    currentZipFileName = baseNameOfZip
    currentZipOutputDir = ""
    orderID,assetName,design_code,product_code= "","","",""
    try:
        f = os.path.join(orderProcessing,zipFile)
        ordersData = {}
        
        with ZipFile(f,'r') as zObject:
            assestLists =[]
            currentZipOutputDir = orderOutputDir+"/"+baseNameOfZip
            Path(currentZipOutputDir).mkdir(parents=True, exist_ok=True)
            zObject.extractall(currentZipOutputDir)
            dbcursor = conn.cursor()
            query = f"SELECT * FROM orders WHERE order_id = '{currentZipFileName}'"
            dbcursor.execute(query)
            order = dbcursor.fetchone()
            
            if order is not None and len(order) > 0:
                query = f"UPDATE orders SET status='PRC', created_date_time='{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' WHERE order_id='{currentZipFileName}'"
                order_ins_id = order[0]
            else:
                query = f"INSERT INTO orders(order_id, status, created_date_time) VALUES('{currentZipFileName}', 'PRC', '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}')"
                dbcursor.execute(query)
                order_ins_id = dbcursor.lastrowid
            conn.commit()
            
            for xmlFile in sorted(Path(currentZipOutputDir).rglob('*.xml')):
                latexSvgFiles = ""
                XMLDir = os.path.splitext(xmlFile)[0].replace(" ","_")
                xmlFilename =  os.path.basename(xmlFile).split('/')[-1]
                xmlFileBasename = os.path.splitext(xmlFilename)[0]
               
                Path(XMLDir).mkdir(parents=True, exist_ok=True)
                xmlFileBasename = xmlFileBasename.replace(" ","_")
                XMLtree = ET.parse(xmlFile)
                XMLRoot = XMLtree.getroot()                    
               
                assetNameList = XMLRoot.find("./OrderItems/OrderItem/Asset/Name").text
                assetNames = assetNameList.split(",")
                product_code = XMLRoot.find("./OrderItems/OrderItem/Asset/Codes/Code").attrib['Value']
                
                assestLists.append(assetNames[0])
                if len(assetNames)==2:
                    assetName = assetNames[1]
                    assestLists.append(assetNames[1])
                else:
                    assetName = assetNames[0]

                design_code = assetName
                dbcursor.execute("UPDATE orders SET tag_list = %s WHERE order_id = %s", (assetNameList, currentZipFileName))
                conn.commit()
                assetName += "_"+product_code.strip() 
          
                dbcursor = conn.cursor(dictionary=True)
               
                dbcursor.execute("SELECT * FROM label_list WHERE label_name = '"+assetName+".svg' ")
                labelDet = dbcursor.fetchone()
                
                if labelDet:
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
                    submitted_date = str(datetime.now().strftime("%d/%m/%Y"))
                else:
                    raise Exception('TAG not found , check tag list')
                
                mandatoryIds=[]
                selected_category = ""
                
                frontAssetName = assetName+"_FRONT"
                frontsvgString = os.path.join(svgDir, frontAssetName + '.svg')
                if os.path.exists(frontsvgString) :
                    frontSideExists = True
                    namespaces = {node[0]: node[1] for _, node in ET.iterparse(frontsvgString, events=['start-ns'])}
                    for key, value in namespaces.items():
                        ET.register_namespace(key, value)
                    frontSVGtree = ET.parse(frontsvgString)
                    frontSvgRoot = frontSVGtree.getroot()  
                    frontSvgName = '1.svg'
                    frontSvgFilePath = currentZipOutputDir+'/'+xmlFileBasename+'/'+frontSvgName
                    labelSize = frontSvgRoot.attrib.get('data-size', '')
                else:
                    frontSideExists = False
                
                tagGroups = {}
                tagSno = 1
                if labelDet['dynamic']==1:   
                    currentAssetName = assetName+"_BACK"
                    currentsvgString = os.path.join(svgDir, currentAssetName + '.svg')
                    if os.path.exists(currentsvgString):
                        currentsvgString = svgDir + '/' + currentAssetName + '.svg'
                    else:
                        currentAssetName = assetName+"_FRONT"
                        currentsvgString = svgDir + '/' + currentAssetName + '.svg'
                        frontSideExists = False
                        
                    currentSvgtree = ET.parse(currentsvgString)
                    currentSvgRoot = currentSvgtree.getroot()
                    
                    selling_price_position_style = get_selling_price_position(currentSvgRoot)
                    
                    currency_india_style = selling_price_position_style.get('currency_india', {}).get('style', None)                 
                    currency_style = selling_price_position_style.get('currency', {}).get('style', None)
                    currency_y_position = selling_price_position_style.get('currency', {}).get('y_position', None)
                    selling_price_fraction_style = selling_price_position_style.get('selling_price_fraction', {}).get('style', None)
                    selling_price_fraction_y_position = selling_price_position_style.get('selling_price_fraction', {}).get('y_position', None)
                    selling_price_style = selling_price_position_style.get('selling_price', {}).get('style', None)
                    size_positions = get_size_position(currentSvgRoot)
                    variable_size_text_style = size_positions.get('variable_size_text', {}).get('style', None)
                    variable_size_box_style = size_positions.get('variable_size_box', {}).get('style', None)
                    variable_size_box_path_style= size_positions.get('variable_size_box_path', {}).get('style', None)
                    
                    namespaces = {node[0]: node[1] for _, node in ET.iterparse(currentsvgString, events=['start-ns'])}
                    for key, value in namespaces.items():
                        ET.register_namespace(key, value)
                    
                    supplierStype,country,color = '','',''
                    all_sizes=[] 
                    tag_size_chart = currentSvgRoot.find(".//*[@id='size_rect_selected']")
                    if tag_size_chart is not None:
                        all_sizes = extract_sizes_from_xml_selected_tag(XMLRoot)                              
                    else:                        
                        all_sizes = extract_sizes_from_xml_all_tag(XMLRoot)    
                    sizes = []
                    selected_size=''
                    
                    items = XMLRoot.findall("./OrderItems/OrderItem/Item")
                    season_code =""
                    for item in items:
                        mandatoryIds = ['quantity']
                        SVGtree = ET.parse(currentsvgString)
                        SVGroot = SVGtree.getroot()
                        itemID = item.find('./ItemID').text
                        qty = item.find('./Quantity').text  
                        status = set_svg_text(SVGroot, 'quantity', f"Qty-{qty}")
                        if status==False:
                            raise Exception("Sorry, Id not found in svg image "+itemID)
                        selling_price= 0
                        selling_price_fraction=00
                        outPutSvgName = itemID+"_"+str(tagSno)+'.svg'
                        currentSvgFilePath=currentZipOutputDir+'/'+xmlFileBasename+'/'+outPutSvgName
                        selected_name_attr =''
                        code128_barcode=''
                        currency=''
                        article_name,barcodenumber='',''
                        var_month,var_year ='',''
                        for size in item.findall("./SizeChartItem/Size"):
                            nameAttr = size.attrib['Name'].replace(' ', '_')
                            nameAttr = re.sub(r'[-_]+', '-', nameAttr).strip('-') 
                            
                            if(nameAttr=='YEARS'):
                                selected_size=size.attrib['Value'] 
                                selected_name_attr=nameAttr   
                                set_svg_text(SVGroot, 'YEARS', size.attrib)
                             
                            if( nameAttr=="ANNI-YEARS"):
                                selected_size=size.attrib['Value'] 
                                selected_name_attr=nameAttr      
                                set_svg_text(SVGroot, 'ANNI-YEARS', size.attrib['Value'])
                            
                            if( nameAttr=="MONTHS"):
                                selected_size=size.attrib['Value'] 
                                selected_name_attr=nameAttr      
                                set_svg_text(SVGroot, 'MONTHS', size.attrib['Value'])
                                
                            elif nameAttr=='CM' :
                                set_svg_text(SVGroot, nameAttr, size.attrib['Value'])                    
                            
                            else:
                                set_svg_text(SVGroot, nameAttr, size.attrib['Value'])
                                if(nameAttr=='ITA' or nameAttr=='IT'):
                                    selected_size=size.attrib['Value']
                                
                                if(nameAttr=='MESI-MONTHS'):
                                    selected_size=size.attrib['Value']
                                    
                        itemVariables = item.findall('./Variables/Variable')
                        
                        for variable in itemVariables:
                            
                            if variable.attrib['Question']=='Season Code':
                                season_code = variable.find("./Answer/AnswerValues/AnswerValue").text
                            
                            if variable.attrib['Question']=='Currency':
                                currency = variable.findall("./Answer/AnswerValues/AnswerValue")
                                
                                for curr in currency:
                                    currency_name = curr.attrib['Name']                            

                                    if(currency_name=='Symbol'):
                                        currency= curr.text                                              
                                    else:
                                        currency=''
                            if variable.attrib['Question']=='Selling Price':
                                answer_value_element = variable.find("./Answer/AnswerValues/AnswerValue")

                                if answer_value_element is not None and answer_value_element.text:
                                    sellingPrice = answer_value_element.text.split(",")                
                                    selling_price= sellingPrice[0]
                                    
                                    if 0 <= 1 < len(sellingPrice):

                                        decimalPrice = sellingPrice[1]
                                    else:
                                        decimalPrice = "00"
                                    selling_price_fraction=","+decimalPrice
                                else:
                                    sellingPrice = None
                                    print("Warning: Selling Price is missing or empty.")                    
                            if variable.attrib['Question']=='SKU Code':
                                skuCode = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                                set_svg_text(SVGroot, 'sku_code', skuCode)
                            
                            if variable.attrib['Question']=='OVS - MAN or WOMAN':
                                humanSize = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'human_size', humanSize)
                                                        
                            if variable.attrib['Question']=='Commercial Ref':
                                commRef = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'commercial_ref', commRef)
                                
                            if variable.attrib['Question']=='Country':
                                country = variable.find("./Answer/AnswerValues/AnswerValue").text
                            if variable.attrib['Question']=='Color':
                                tag_color = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'tag_color', tag_color)
                                
                            if variable.attrib['Question']=='Style Code':
                                styleCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'style_code', styleCode)
                                
                            if variable.attrib['Question']=='Material(Model Code)':
                                material_model_code = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'material_model_code', material_model_code)
                                
                            if variable.attrib['Question']=='Article name':
                                article_name = variable.find("./Answer/AnswerValues/AnswerValue").text
                               
                            if variable.attrib['Question']=='Color Code':
                                colorCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'color_code', colorCode)
                            
                            if variable.attrib['Question']=='Supplier Style':
                                supplierStype = variable.find("./Answer/AnswerValues/AnswerValue").text              
                                
                            if variable.attrib['Question']=='Translation Code':
                                translations = variable.findall("./Answer/AnswerValues/AnswerValue")
                                for translation in translations:
                                    lang = translation.attrib['Name'].upper()        
                                    set_svg_text(SVGroot, f'translation_code_{lang}', translation.text)

                            if variable.attrib['Question']=='Material Type':
                                translations = variable.findall("./Answer/AnswerValues/AnswerValue")
                                for translation in translations:
                                    lang = translation.attrib['Name']                      
                                    set_svg_text(SVGroot, f'material_type_{lang}', translation.text)

                            if variable.attrib['Question']=='Apparel Categories':
                                ApparelCategory = variable.find("./Answer/AnswerValues/AnswerValue").text                      
                                set_svg_text(SVGroot, 'apparel_categories', ApparelCategory) 
                                selected_category=ApparelCategory                      
                            
                            if variable.attrib['Question']=='Department':
                                department = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                                set_svg_text(SVGroot, 'department', department)

                            if variable.attrib['Question']=='COMMODITY':
                                commodity = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                                set_svg_text(SVGroot, 'commodity', commodity)

                            if variable.attrib['Question']=='Net Quantity':
                                net_quantity = variable.find("./Answer/AnswerValues/AnswerValue").text                        
                                set_svg_text(SVGroot, 'net_quantity', net_quantity)
                            
                            if variable.attrib['Question']=='OKEO-TEX':
                                okeo_tex_value = variable.find("./Answer/AnswerValues/AnswerValue").text 
                                set_category(SVGroot,f"okeo_tex_{okeo_tex_value}") 
                                                  
                            if variable.attrib['Question']=='MONTH':
                                var_month = variable.find("./Answer/AnswerValues/AnswerValue").text  
                                
                            if variable.attrib['Question']=='YEAR':
                                var_year = variable.find("./Answer/AnswerValues/AnswerValue").text
                                
                            if variable.attrib['Question']=='Sub Department':
                                subdepartment = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'sub_department', subdepartment)                           
                                
                            if variable.attrib['Question']=='Barcode Number':
                                barcodenumber = variable.find("./Answer/AnswerValues/AnswerValue").text
                                bar1 = barcodenumber[0] 
                                bar2 = barcodenumber[1:7]
                                bar3 = barcodenumber[7:]
                                bar_values = {'bar1': bar1,'bar2': bar2,'bar3': bar3 }
                                
                                for bar_id, bar_text in bar_values.items():
                                    set_svg_text(SVGroot, f'{bar_id}', bar_text)

                                barcodeArea = SVGroot.find(".//*[@id='Barcode']")
                                if barcodeArea is not None:
                                    for rect in barcodeArea:
                                        labelDet['barcode_x_position'] = rect.attrib['x']
                                        labelDet['barcode_y_position'] = rect.attrib['y']
                                        break                                
                                else:
                                    raise Exception("Barcode area not found in svg image")
                                
                            if variable.attrib['Question']=='EAN 128C':
                                code128_barcodenumber = variable.find("./Answer/AnswerValues/AnswerValue").text
                                code128_barcode=code128_barcodenumber
                                set_svg_text(SVGroot, 'ean_128c', code128_barcode)
                                code128_barcodeArea = SVGroot.find(".//*[@id='Barcode_ean_128c']")
                                
                                if code128_barcodeArea is not None:
                                    
                                    for rect in code128_barcodeArea:
                                        labelDet['code128_barcode_x_position'] = rect.attrib['x']
                                        labelDet['code128_barcode_y_position'] = rect.attrib['y']
                                        break  
                                else:
                                    raise Exception("Barcode code 128 id not found in svg image")
                                
                        if selected_category !='':
                            set_category(SVGroot,selected_category)  
                        else:
                            set_category(SVGroot,selected_name_attr)
                        if var_month and var_year:
                            set_svg_text(SVGroot, 'month_year', f"{var_month}-{var_year}")
                        
                        tagGroups.setdefault(country, {}).setdefault(color, {}).setdefault(supplierStype, {}).setdefault('tagList',[]).append(outPutSvgName)
                        
                        if barcodenumber !='':
                            set_barcode(labelDet['barcode_x_position'],labelDet['barcode_y_position'],labelDet['ean13_barcode_width'],barcodenumber,SVGroot)
                            
                        if code128_barcode !='':
                            set_code128_barcode(labelDet['code128_barcode_x_position'],labelDet['code128_barcode_y_position'],labelDet['code128_barcode_width'],code128_barcode,SVGroot)
                            
                        if selected_size!='':
                          
                            if tag_size_chart is not None:
                                                                 
                                        int_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL','3XL','XXXL','4XL']
                                        int_rank = {size: index for index, size in enumerate(int_order)}
                                        int_index = all_sizes[0].index('INT')
                                        sorted_array = [all_sizes[0]] + sorted(
                                            all_sizes[1:], key=lambda x: int_rank.get(x[int_index], float('inf'))
                                        )
                                        add_text_boxes_to_svg(SVGroot, sorted_array, selected_size,variable_size_box_style, variable_size_text_style)
                            else:   
                                
                                size_order= sort_dynamic_list(all_sizes)                               
                                tag_size_chart_circle = SVGroot.find(".//*[@id='size_oval_1']") 
                                               
                                if tag_size_chart_circle is not None:  
                                                                    
                                    if len(all_sizes) !=0:                                       
                                        size_append_circle(SVGroot,'size_oval_1',size_order,selected_size,variable_size_text_style,variable_size_box_style,variable_size_box_path_style)
                                        size_append_circle(SVGroot,'size_oval_2',size_order,selected_size,variable_size_text_style,variable_size_box_style,variable_size_box_path_style)                   
                                else:
                                    tag_size = SVGroot.find(".//*[@id='size_rect']") 
                                    
                                    if tag_size is not None: 
                                        if len(all_sizes) !=0: 
                                            size_append(SVGroot,size_order,selected_size,variable_size_text_style,variable_size_box_style)               
                     
                        selling_price_type = currentSvgRoot.find(".//*[@id='selling_price_full']")
                        
                        if selling_price_type is None:
                            
                            if currency=="₹":           
                                selling_price_append(SVGroot,currency,selling_price,selling_price_fraction,currency_y_position,selling_price_fraction_y_position,currency_india_style,selling_price_fraction_style,selling_price_style)
                            else:                           
                                selling_price_append(SVGroot,currency,selling_price,selling_price_fraction,currency_y_position,selling_price_fraction_y_position,currency_style,selling_price_fraction_style,selling_price_style)
                        else:
                            print(f"currency-{currency},selling_price- {selling_price}{selling_price_fraction}")
                            set_svg_text(SVGroot, 'selling_price_full', f"{currency} {selling_price}{selling_price_fraction}")
                            
                        if selected_category !='':
                            set_apperal_category(SVGroot, selected_category) 
                     
                        SVGtree.write(currentSvgFilePath,encoding='utf-8', xml_declaration=True)
                        #svg file generation end of xml file end
                        tagSno +=1
                    
                    latexSvgFilesCode = ""
                    if frontSideExists:
                        if season_code!="":
                            set_svg_text(frontSvgRoot,"season_code","("+str(season_code)+")")
                        frontSVGtree.write(frontSvgFilePath)

                        frontSvgBaseName = os.path.splitext(frontSvgName)[0]
                        width, height = get_svg_dimensions(frontSvgFilePath)
                        latexSvgFilesCode =f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{frontSvgBaseName}}} \n' 
                        latexSvgFilesCode += '\\vspace{2mm}  \n'  
                        latexSvgFilesCode += '\\hspace{6mm}  \n' 
                                          
                    font_families = extract_font_families_from_style(currentSvgFilePath)
                    print (f"font Familes : {font_families}")
                    width, height = get_svg_dimensions(currentSvgFilePath)
                    print (f"svg width : {width} svg height :{height}")
                    
                    isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                    if isPDFOutputDir==False:
                        Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)

                    buyerTxt         = '               OVS'
                    
                    pdfFileName = (assetName+"_"+baseNameOfZip).replace(" ","_")
                    latexFileName = pdfFileName
                    latexFilePath = Path(currentZipOutputDir) / "pdf" / f"{latexFileName}.tex"
                    latexFile = Path(latexFilePath)
                    latexFile.touch(exist_ok= True)
                    graphicspath = currentZipOutputDir+'/'+xmlFileBasename
                    latexFonts = ""
                    
                    svg_dir = Path(currentZipOutputDir) / xmlFileBasename
                    pdfPageBody =""
                    
                    for country, colorGroups in tagGroups.items():
                        for color, supplierGroups in colorGroups.items():
                            for supplierStyle, tagData in supplierGroups.items():                
                                tagList = tagData.get('tagList', [])
                                title = " - ".join(filter(None, [supplierStyle, country, color, orderID]))
                                pdfPageBody += r'''\renewcommand{\arraystretch}{1.5}
                        \begin{table}[h]
                        \centering
                           \begin{tabular}{|p{8cm}|p{11cm}|p{8cm}|} 
                            \hline
                           \multirow{6}{8cm}{ \centering \includegraphics[height=1.7cm,width=3.9cm]{Sainmarknewlogo} }   & BUYER : '''+buyerTxt+r''' & \multirow{6}{8cm}{\centering \makecell{ARTWORK \\ FOR\\ APPROVAL}} \\
                            \cline{2-2}
                            & CUSTOMER : '''+customerName.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & DESIGN CODE : '''+design_code.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & PRODUCT CODE : '''+product_code.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & SUBMITTED DATE : '''+submitted_date+r''' & \\
                            \cline{2-2}
                            &  & \\
                            \hline
                        \end{tabular}
                    \end{table}
                         \afterpage{\begin{table}[h]
                        \centering
                           \begin{tabular}{|p{8cm}|p{11cm}|p{8cm}|} 
                            \hline
                           \multirow{6}{8cm}{ \centering \includegraphics[height=1.7cm,width=3.9cm]{Sainmarknewlogo} }   & BUYER : '''+buyerTxt+r''' & \multirow{6}{8cm}{\centering \makecell{ARTWORK \\ FOR\\ APPROVAL}} \\
                            \cline{2-2}
                            & CUSTOMER : '''+customerName.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & DESIGN CODE : '''+design_code.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & PRODUCT CODE : '''+product_code.replace("_","\\_").replace("&","\\&")+r''' & \\
                            \cline{2-2}
                            & SUBMITTED DATE : '''+submitted_date+r''' & \\
                            \cline{2-2}
                            &  & \\
                            \hline
                        \end{tabular}
                    \end{table}
                    }
                        \begin{center}
                        {\Large \textbf{\fontspec{Arial}\textcolor{red}{'''+title+r'''}}}
                        \end{center}
                        \hfill \break
                        \centering '''
                                    
                                for tag in tagList:
                                    svg_path = Path(currentZipOutputDir) / xmlFileBasename / tag
                                    baseNameSVG = os.path.splitext(tag)[0]
                                    width, height = get_svg_dimensions(svg_path)
                                    latexSvgFilesCode +=f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{baseNameSVG}}} \n'   
                                    latexSvgFilesCode += '\\vspace{2mm}  \n'  
                                    latexSvgFilesCode += '\\hspace{6mm}  \n' 
                                pdfPageBody += latexSvgFilesCode+"\n\\newpage"
                    
                    with open(latexFilePath,'w') as clatexFile:
                        clatexFile.write(r'''\documentclass{article}
                        \usepackage{multirow}
                        \usepackage{makecell}
                        \usepackage{graphicx}
                        \usepackage[export]{adjustbox}
                        \usepackage{xcolor}
                        \usepackage[inkscapelatex=false]{svg}
                        %\usepackage[a3paper,landscape,left=5mm,right=5mm,bottom=5mm]{geometry}
                        \usepackage[b2paper,landscape,left=10mm,right=10mm,bottom=10mm]{geometry}
                        \setlength{\voffset}{-0.75in}
                        \setlength{\headsep}{5pt}
                        \usepackage{layout}
                        \usepackage{fontspec}
                        \usepackage{afterpage}
                        \newcolumntype{Y}{>{\centering\arraybackslash}X}
                        \renewcommand{\arraystretch}{1.2}
                        \graphicspath{{'''+graphicspath+r'''}}
                        %\IfFontExistsTF{Arial-Bold}{\newfontfamily\Arial{Arial}}{\textbf{Warning: Font Arial not found.}}
                        '''+latexFonts+r'''
                        \begin{document}
                            '''+pdfPageBody+r'''
                        \end{document} ''')
                        
                    # * dynamic tag latex creation end        

                else:
                    print('static label')
                    supplierStype,country,color = '','',''
                    items = XMLRoot.findall("./OrderItems/OrderItem/Item")
                    for item in items:
                        itemID = item.find('./ItemID').text
                        qty = item.find('./Quantity').text
                        status = set_svg_text(frontSvgRoot, 'quantity', f"Qty - {qty}")
                        if status==False:
                            raise Exception("Sorry, not found in svg image "+itemID)
                        
                        itemVariables = item.findall('./Variables/Variable')
                        for variable in itemVariables:
                           if variable.attrib['Question']=='Supplier Style':
                                supplierStype = variable.find("./Answer/AnswerValues/AnswerValue").text
                           if variable.attrib['Question']=='Country':
                                country = variable.find("./Answer/AnswerValues/AnswerValue").text
                        
                    currentSvgFilePath=currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg'
                    frontSVGtree.write(currentSvgFilePath,encoding='utf-8', xml_declaration=True)
                    
                    isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                    if isPDFOutputDir==False:
                        Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                
                    title = supplierStype+" - "+country+" - "+orderID
                    buyerTxt         = '               OVS'
                    
                    pdfFileName = (assetName+"_"+baseNameOfZip).replace(" ","_")
                    latexFileName = pdfFileName
                    latexFilePath = Path(currentZipOutputDir) / "pdf" / f"{latexFileName}.tex"
                    latexFile = Path(latexFilePath)
                    latexFile.touch(exist_ok= True)
                    graphicspath = currentZipOutputDir+'/'+xmlFileBasename
                    latexFonts = ""
                    
                    svg_dir = Path(currentZipOutputDir) / xmlFileBasename
                    for svg in sorted(os.listdir(svg_dir)):
                        if svg.endswith(".svg"):
                            svg_path = Path(currentZipOutputDir) / xmlFileBasename / svg
                            baseNameSVG = os.path.splitext(svg)[0]
                            width, height = get_svg_dimensions(svg_path)
                            print(f"width : {width}   height : {height}")          
                            latexSvgFiles +=f'\\includesvg[inkscapearea=page, width=0.666\\linewidth]{{{baseNameSVG}}} \n'             
                    with open(latexFilePath,'w') as clatexFile:
                        clatexFile.write(r'''\documentclass{article}
                        \usepackage{multirow}
                        \usepackage{makecell}
                        \usepackage{graphicx}
                        \usepackage[export]{adjustbox}
                        \usepackage{xcolor}
                        \usepackage[inkscapelatex=false]{svg}
                       %\usepackage[a3paper,left=5mm,right=5mm,bottom=5mm]{geometry}
                        \usepackage[b2paper,landscape,left=5mm,right=5mm,bottom=5mm,top=5mm]{geometry}
                        \setlength{\voffset}{-0.75in}
                        \setlength{\headsep}{80pt}
                        \usepackage{layout}
                        \usepackage{fontspec}
                        \newcolumntype{Y}{>{\centering\arraybackslash}X}
                        \renewcommand{\arraystretch}{1.2}
                        \graphicspath{{'''+graphicspath+r'''}}
                        '''+latexFonts+r'''
                        \begin{document}
                        \begin{table}[h]
                        \centering
                           \begin{tabular}{|p{8cm}|p{11cm}|p{8cm}|} 
                            \hline
                           \multirow{6}{8cm}{ \centering \includegraphics[height=1.7cm,width=3.9cm]{Sainmarknewlogo} }   & BUYER : '''+buyerTxt+r''' & \multirow{6}{8cm}{\centering \makecell{ARTWORK \\ FOR\\ APPROVAL}} \\
                            \cline{2-2}
                            & CUSTOMER : '''+customerName.replace("_","\_").replace("&","\&")+r''' & \\
                            \cline{2-2}
                            & DESIGN CODE : '''+design_code.replace("_","\_").replace("&","\&")+r''' & \\
                            \cline{2-2}
                            & PRODUCT CODE : '''+product_code.replace("_","\_").replace("&","\&")+r''' & \\
                            \cline{2-2}
                            & SUBMITTED DATE : '''+submitted_date+r''' & \\
                            \cline{2-2}
                            &  & \\
                            \hline
                         \end{tabular}
                        \end{table}
                        \begin{center}
                           \hfill \break
                           \hfill \break
                            {\Large \textbf{\fontspec{Arial-Bold}\textcolor{red}{'''+title+r'''}}}
                           \break
                           \break
                           \break
                           {\Large  \textbf{\fontspec{ArialMT}{'''+labelSize+r'''}}}
                        \end{center}
                         \hfill \break
                        \centering 
                        '''+latexSvgFiles+r'''
                        \end{document} ''')
                                  
                    # *static tag latex creation end
                
                latexFilePathStr = current_dir+"/"+str(latexFilePath)
                outputDirStr = current_dir+"/"+str(Path(currentZipOutputDir) / "pdf")   
                
                #! To run the xelatex command in terminal
                x = os.system(f'xelatex --shell-escape --enable-write18 --output-directory="{outputDirStr}" "{latexFilePathStr}"')
                # reduce_pdf_quality(f'{outputDirStr}/{pdfFileName}.pdf',f'{outputDirStr}/{pdfFileName}_compressed.pdf')
                #! to remove the original pdf file
                #os.remove(f'{outputDirStr}/{pdfFileName}.pdf')
            if ordersData:
                order_id = list(ordersData.keys())[0]
                toemail = ordersData[order_id].get('customerEmail')
                approval_mail_status = 'P'
                submitted_date = str(datetime.now().strftime("%Y-%m-%d"))
                
                dbcursor = conn.cursor()
                dbcursor.execute("UPDATE orders SET buyer = %s, customer_id = %s, customer_name = %s, customer_email_id = %s, approval_mail_status = %s, submitted_date = %s, status = %s, created_date_time = %s WHERE order_id = %s", 
                                 ('OVS', ordersData[order_id].get('customerID'), ordersData[order_id].get('customerName'), ordersData[order_id].get('customerEmail'), approval_mail_status, submitted_date, 'CAP', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), order_id))
                conn.commit()
                                    
            res = send_mail(subject=baseNameOfZip,toMailid=toemail,attachmentPath=currentZipOutputDir+'/pdf')
            
            if res['status']=='success':
                approval_mail_status = 'S'
                shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', customerApprovalPending+'/'+baseNameOfZip+'.zip')
            else:
                approval_mail_status = 'F'
                shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', failedOrders+'/'+baseNameOfZip+'.zip')
                dbcursor = conn.cursor()
                query = "SELECT COUNT(*) FROM failed_orders WHERE order_id = %s"
                print(f"Executing query: {query} with data: {currentZipFileName}")
                dbcursor.execute(query, (currentZipFileName,))
                count = dbcursor.fetchone()[0]

                if count > 0:
                    update_query = """
                    UPDATE failed_orders 
                    SET tag_list = %s, error = %s, status = %s, created_date_time = %s 
                    WHERE order_id = %s
                    """
                    update_values = (",".join(assestLists), res['msg'], 'F', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), currentZipFileName)
                    
                    # formatted_update_query = update_query.replace("%s", "{}").format(*map(repr, update_values))
                    # print("Executing Query:", formatted_update_query)

                    dbcursor.execute(update_query, update_values)
                else:
                    insert_query = """
                    INSERT INTO failed_orders(order_id, tag_list, error, status, created_date_time) 
                    VALUES(%s, %s, %s, %s, %s)
                    """
                    insert_values = (currentZipFileName, ",".join(assestLists), res['msg'], 'F', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
                    
                    # formatted_insert_query = insert_query.replace("%s", "{}").format(*map(repr, insert_values))
                    # print("Executing Query:", formatted_insert_query)

                    dbcursor.execute(insert_query, insert_values)
                
                print(approval_mail_status)
                print(order_ins_id)
                # Update approval_mail_status
                update_order_query = "UPDATE orders SET approval_mail_status = %s WHERE id = %s"
                update_order_values = (approval_mail_status, order_ins_id)

                # formatted_update_order_query = update_order_query.replace("%s", "{}").format(*map(repr, update_order_values))
                # print("Executing Query:", formatted_update_order_query)

                dbcursor.execute(update_order_query, update_order_values)

                # Commit transaction
                conn.commit()
            
            delete_folder_and_files(currentZipOutputDir)
            delete_folder_contents_only('svg-inkscape')
                
    except Exception as error:
        print('Error')
        print(error)       
        shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', failedOrders+'/'+baseNameOfZip+'.zip')  
        delete_folder_and_files(currentZipOutputDir)
        dbcursor = conn.cursor()
        print(f"Executing query: SELECT COUNT(*) FROM orders WHERE order_id = '{currentZipFileName}'")
        dbcursor.execute("SELECT COUNT(*) FROM orders WHERE order_id = %s", (currentZipFileName,))
        order_count = dbcursor.fetchone()[0]
        if order_count > 0:
            dbcursor.execute("UPDATE orders SET status = %s WHERE order_id = %s", ('F', currentZipFileName))
            
        dbcursor.execute("SELECT COUNT(*) FROM failed_orders WHERE order_id = %s", (currentZipFileName,))
        count = dbcursor.fetchone()[0]
        if count > 0:
            dbcursor.execute("UPDATE failed_orders SET tag_list = %s, error = %s, status = %s, created_date_time = %s WHERE order_id = %s", 
                     (assetName, str(format(error)).replace("'", '"').strip(), 'F', datetime.now().strftime("%Y-%m-%d %H:%M:%S"), currentZipFileName))
        else:
            dbcursor.execute("INSERT INTO failed_orders(order_id, tag_list, error, status, created_date_time) VALUES(%s, %s, %s, %s, %s)", 
                     (currentZipFileName, assetName, str(format(error)).replace("'", '"').strip(), 'F', datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
            
def reduce_pdf_quality(input_pdf, output_pdf, dpi=100, quality=90):
    images = convert_from_path(input_pdf, dpi=dpi)  # Convert to images

    pdf = FPDF(orientation="P", unit="mm", format="A3")
    for img in images:
        img = img.convert("RGB")  # Ensure correct format
        img.save("temp.jpg", "JPEG", quality=quality)  # Reduce quality

        pdf.add_page()
        pdf.image("temp.jpg", x=0, y=0, w=297, h=420)  # A3 width

    pdf.output(output_pdf, "F")

def add_background_to_svg(svg_path, background_image_path, angle=45, opacity=0.2):
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Set rotation center (adjust if needed)
    width = root.attrib.get('width', '100%')  # Get SVG width
    height = root.attrib.get('height', '100%')  # Get SVG height
    cx, cy = "50", "50"  # Center of rotation (default to center)

    # Create the background image element with rotation and opacity
    bg_image = ET.Element('image', {
        'x': '0',
        'y': '0',
        'width': '100%',
        'height': '100%',
        'href': background_image_path,  # Link to background image
        'style': f'opacity: {opacity};',  # Set opacity
        'transform': f'rotate({angle}, {cx}, {cy})'  # Apply rotation
    })

    # Insert the background image at the beginning
    root.insert(0, bg_image)

    # Save the modified SVG
    tree.write(svg_path, encoding='utf-8', xml_declaration=True)

def set_svg_text(svg_root, element_id, text_value):
    elements = svg_root.findall(f".//*[@id='{element_id}']")

    if elements:
        for element in elements:
            tspan = element.find("tspan")
            if tspan:
                targetElement = tspan
            else:
                targetElement = element
            targetElement.text = ""
            targetElement.text = text_value
        return True
    else:
        if element_id not in mandatoryIds:
            return False

def get_rects_as_string(file_path):   
    tree = ET.parse(file_path)
    root = tree.getroot()  
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    ET.register_namespace('', namespace["svg"])    
    rects = root.findall(".//svg:rect", namespace)       
    rects_content = ""
    
    for rect in rects:
        attribs = {k: v for k, v in rect.attrib.items() if k != "xmlns"}
        attribs_string = " ".join([f'{key}="{value}"' for key, value in attribs.items()])
        rect_string = f"<rect {attribs_string} />"
        rects_content += rect_string + "\n"
        
    return rects_content.strip()
    
def set_barcode(x, y, width, data, root):
    generator = bc.BarcodeGenerator()
    barcodeno = data       
    x = float(x)      
    x = x - 10.5
    y = float(y)
    if width == '' or width is None:
        print("Ean 13 barcode width is not given")
        return
    width = float(width)  
    width = width+1
    default_array = {
        "barcodeWidth": width,
        "barcodeHeight": 23,
        "color": 'cmyk(0,0,0,100)',
        "x": x,
        "y": y,
        "showCode": False,
        "inline": True,
        "barWidthRatio": 0.7,
        "quietZone": 10
    }
    svg_output = generator.get_barcode_svg(barcodeno, "EAN13", default_array)  
    directory = "barcode_svg"
    filename = f"{barcodeno}.svg"
    file_path = os.path.join(directory, filename)
    os.makedirs(directory, exist_ok=True)    
    
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(svg_output)
    bars_content = get_rects_as_string(file_path) 
    bars_content = bars_content.strip()  

    if not bars_content:
        print("Error: No bars content")
        return {"error": "No bars content", "status_code": 400}
    try:
        bars_content = f'<svg xmlns="http://www.w3.org/2000/svg">{bars_content}</svg>' 
        namespaces = {'ns0': 'http://www.w3.org/2000/svg'}       
        bars_element = ET.fromstring(bars_content)     
        barcodeArea = root.find(".//*[@id='Barcode']", namespaces)
        barcodeArea.clear()
        if barcodeArea is not None:             
          
            for elem in bars_element.iter():
                
                if '}' in elem.tag:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag.split('}')[1]}"
                else:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag}"
            # Append the new barcode
            barcodeArea.append(bars_element)
        else:
            print("No <rect> element found with id='barcode'.")
            return {"error": "No <rect> element found with id='barcode'.", "status_code": 404}

        return {"message": "SVG updated successfully"}

    except ET.ParseError as e:
        print( f"SVG parsing error: {str(e)}")
        return {"error": f"SVG parsing error: {str(e)}", "status_code": 500}
    finally:
               
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Temporary file {file_path} deleted.")

def get_svg_dimensions(svg_file_path):
    tree = ET.parse(svg_file_path)
    root = tree.getroot()
    
    viewbox = root.attrib.get('viewBox')
    
    if not viewbox:
        raise ValueError("SVG does not have viewBox, width, or height attributes.")
    
    _, _, width_user_units, height_user_units = map(float, viewbox.split())
    
    mm_per_unit = 0.352778
    width_mm = width_user_units * mm_per_unit
    height_mm = height_user_units * mm_per_unit

    return width_mm, height_mm

def size_append(root, size_ranges, selected_size, variable_size_text_style, variable_size_box_style):
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)
    rect_element = root.find(".//*[@id='size_rect']")
    if rect_element is None:
     raise ValueError("Rectangle with id 'size_rect' not found.")
    rect_x = float(rect_element.attrib["x"])
    rect_y = float(rect_element.attrib["y"])
    rect_width = float(rect_element.attrib["width"])
    rect_height = float(rect_element.attrib["height"])
    padding = 0
    usable_width = rect_width - 2 * padding
    usable_start_x = rect_x + padding
    row_start_y = rect_y + 1
    base_element_width = 12  
    base_alpha_element_width = 8  
    element_height = 10
    vertical_spacing = 2
    horizontal_spacing = 8.5
    size_count = len(size_ranges)
    all_alphabetic = all(label[0].isalpha() for label in size_ranges)  
    if rect_width <=85:
        if not all_alphabetic:
            horizontal_spacing = 9
            base_element_width = 14
                    
        
        if size_count <= 4:
            columns = size_count
        elif size_count == 5 and all_alphabetic:
            columns = 5  
        elif size_count == 5:
            columns = 3
        elif size_count == 6:
            columns = 3
        elif size_count in [7, 8, 9]:
            columns = 4
        else:
            columns = 4  
    else:
        if size_count <= 5:
            columns = size_count
        elif size_count == 6 and all_alphabetic:
            columns = 6  
        elif size_count == 6:
            columns = 4
        elif size_count in [7, 8, 9]:
            columns = 5
        else:
            columns = 5  
    
    rows = (size_count + columns - 1) // columns
    total_height = rows * element_height + (rows - 1) * vertical_spacing
    

    if columns <= 5:
        row_start_y = rect_y + (rect_height - total_height) / 2  
    else:
        row_start_y = rect_y + 1 
    for row in range(rows):
        elements_in_row = min(columns, len(size_ranges) - row * columns)
        total_row_width = 0
        size_widths = []     
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
            element_width = base_alpha_element_width if label[0].isalpha() else base_element_width
            if label in ["XXL", "XXXL"]:
                element_width *= 1.5
            size_widths.append(element_width)
            total_row_width += element_width
        total_row_width += (elements_in_row - 1) * horizontal_spacing
        total_elements_width = sum(size_widths) + (elements_in_row - 1) * horizontal_spacing
        
        if columns <= 5:
            
            start_x = usable_start_x + (usable_width - total_elements_width) / 2  
        else:
            start_x = usable_start_x  
        
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
            element_width = base_alpha_element_width if label[0].isalpha() else base_element_width
            rect_x = start_x + sum(size_widths[:col]) + col * horizontal_spacing
            rect_y = row_start_y + row * (element_height + vertical_spacing)
            text_x = rect_x + element_width / 2
            text_y = rect_y + element_height / 2
            
            rect_element = ET.Element(
                "rect",
                {
                    "id": f"box_{label}",
                    "x": str(rect_x - 3.5),
                    "y": str(rect_y - 1),
                    "width": str(element_width + 7),
                    "height": str(element_height),
                    "style": "display:inline" if label == selected_size else "display:none",
                },
            )
            root.append(rect_element)
            style_box = f"{variable_size_box_style} display{':inline' if label == selected_size else ':none'} "
            text_box_element = ET.Element("text", {
                "id": f"variable_Size_box_{label}",
                "style": style_box,
                "transform": f"translate({text_x} {text_y})",
                "text-anchor": "middle",
                "dominant-baseline": "middle",
            })
            tspan_box_element = ET.SubElement(text_box_element, "tspan", {"x": "0", "y": "0"})
            tspan_box_element.text = label
          
            root.append(text_box_element)
            style_text = f"{variable_size_text_style} display{':none' if label == selected_size else ':inline'} "
            text_element = ET.Element("text", {
                "id": f"variable_Size_{label}",
                "style": style_text,
                "transform": f"translate({text_x} {text_y})",
                "text-anchor": "middle",
                "dominant-baseline": "middle",
            })
            tspan_element = ET.SubElement(text_element, "tspan", {"x": "0", "y": "0"})
            tspan_element.text = label
            root.append(text_element)
    
def set_category(root,selected_category):  
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    selected_element = root.find(f".//svg:g[@id='{selected_category}']", namespace)
    if selected_element is not None:
        selected_element.attrib.pop('display', None) 
        print(f"Element with ID '{selected_category}' is now visible.")
    else:
        print(f"No element found with ID '{selected_category}'.")
        
    print(f"SVG updated.")
    
def extract_font_families_from_style(svg_file):
    font_families = set()
   
    with open(svg_file, 'r', encoding='utf-8') as file:
        svg_content = file.read()
   
    soup = BeautifulSoup(svg_content, 'xml')
    style_tag = soup.find('style')
    
    if style_tag:
        style_content = style_tag.string
        font_matches = re.findall(r'font-family:\s*([^;]+);', style_content)
  
        for font in font_matches:
            clean_fonts = [f.strip().strip("'\"") for f in font.split(',')]
            font_families.update(clean_fonts)

    return list(font_families)

# get extract class from currency and translate y position
def extract_transform_and_style(element):
        transform = element.attrib.get('transform', '')
        style_attr = element.attrib.get('style', '')
        y_position = None
        if transform:           
            match = re.search(r'translate\(([-\d.]+)[, ]+([-\d.]+)\)', transform)
            if match:               
                y_position = match.group(2)  
        return y_position, style_attr
    
def get_selling_price_position(root):  
    SVG_NS = "{http://www.w3.org/2000/svg}"
    price_price_position = {}   
   
    currency_element = root.find(".//" + SVG_NS + "text[@id='currency']")
    if currency_element is not None:
        y_position, style_attr = extract_transform_and_style(currency_element)
        price_price_position['currency'] = {'y_position': y_position, 'style': style_attr}

    currency_element_india = root.find(".//" + SVG_NS + "text[@id='currency_india']")
    if currency_element_india is not None:
        y_position, style_attr = extract_transform_and_style(currency_element_india)
        price_price_position['currency_india'] = {'y_position': y_position, 'style': style_attr}
    
    selling_price_element = root.find(".//" + SVG_NS + "text[@id='selling_price']")
    if selling_price_element is not None:
        y_position, style_attr = extract_transform_and_style(selling_price_element)
        price_price_position['selling_price'] = {'y_position': y_position, 'style': style_attr}
    
    selling_price_fraction_element = root.find(".//" + SVG_NS + "text[@id='selling_price_fraction']")
    if selling_price_fraction_element is not None:
        y_position, style_attr = extract_transform_and_style(selling_price_fraction_element)
        price_price_position['selling_price_fraction'] = {'y_position': y_position, 'style': style_attr}

    return price_price_position   

def get_size_position(root):
    SVG_NS = "{http://www.w3.org/2000/svg}"
    size_positions = {}   
    variable_size_text_element = root.find(".//" + SVG_NS + "text[@id='variable_size_text']")
    if variable_size_text_element is not None:
        y_position, style_attr = extract_transform_and_style(variable_size_text_element)
        size_positions['variable_size_text'] = {'y_position': y_position, 'style': style_attr}

    variable_size_box_element = root.find(".//" + SVG_NS + "text[@id='variable_size_box']")
    if variable_size_box_element is not None:
        y_position, style_attr = extract_transform_and_style(variable_size_box_element)
        size_positions['variable_size_box'] = {'y_position': y_position, 'style': style_attr}
    variable_size_box_path_element = root.find(".//" + SVG_NS + "path[@id='size_path']")
    if variable_size_box_path_element is not None:
        y_position, style_attr = extract_transform_and_style(variable_size_box_path_element)
        size_positions['variable_size_box_path'] = {'y_position': y_position, 'style': style_attr}
    return size_positions

# selling price and currency value updated in svg
def selling_price_append(root, currency_symbol,selling_price,selling_price_fraction_part,currency_y_position, selling_price_y_position, currency_style, selling_price_fraction_style,selling_price_style):
    if selling_price == 0:
        return      
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)
   
    viewBox = root.attrib.get("viewBox", "0 0 100 100").split()
    svg_width = float(viewBox[2])
    print(f"svg_width: {svg_width}")
    char_widths = {
        "0": 9.5, "1": 5.0, "2": 9.5, "3": 9.5, "4": 9.5,
        "5": 9.5, "6": 9.5, "7": 6.5, "8": 9.5, "9": 9.5
    }
    default_char_width = 11.5
    char_width = 9.5
    spacing = 5 
    # if currency_symbol=="₹":
    #     spacing = 9 
    currency_width = len(currency_symbol) * char_width
    selling_price_width = sum(char_widths.get(char, default_char_width) for char in selling_price)
    decimal_width = len(selling_price_fraction_part) * char_width

    total_width = currency_width + selling_price_width + decimal_width + (2 * spacing)
    base_currency_x = (svg_width - total_width) / 2
    currency_x_position = base_currency_x +3

    selling_price_x = currency_x_position + currency_width + spacing
    combined_length = len(selling_price) + len(currency_symbol)  
    decimal_x = selling_price_x + selling_price_width +((combined_length+1)*2.2)
  
    if selling_price_y_position !=None:
        currency_element = ET.Element("text", {
            "id": "currency_selling_price",
            "style": currency_style,
            "transform": f"translate({currency_x_position} {currency_y_position} )",
        })
        tspan_currency = ET.SubElement(currency_element, "tspan", {"x": "0", "y": "0"})
        tspan_currency.text = f"{currency_symbol}"
        tspan_price  = ET.SubElement(currency_element, "tspan", {"style": selling_price_style,"dx": "4" })
        tspan_price .text = f"{selling_price } "
        root.append(currency_element)
        decimal_element = ET.Element("text", {
            "style": selling_price_fraction_style,
            "transform": f"translate({decimal_x} {selling_price_y_position})",
        })
        tspan_decimal = ET.SubElement(decimal_element, "tspan", {"x": "0", "y": "0"})
        tspan_decimal.text = selling_price_fraction_part
        root.append(decimal_element) 
       
    else:
        currency_element = ET.Element("text", {
            "id": "currency_selling_price",
            "style": currency_style,
            "transform": f"translate({currency_x_position} {currency_y_position} )",
        })
        tspan_currency = ET.SubElement(currency_element, "tspan", {"x": "0", "y": "0"})
        tspan_currency.text = f"{currency_symbol} {selling_price }{selling_price_fraction_part} "
        root.append(currency_element)
    # tree.write(svg_file, xml_declaration=True, encoding="utf-8")
    # print(f"SVG updated and saved to {svg_file}")

def parse_range_or_size(value):
  
    if '-' in value and value.replace('-', '').isdigit():
        return int(value.split('-')[0])
   
    size_order = ["XS","S", "M", "L", "XL", "XXL","XXXL","3XL"]
    if value in size_order:
        return size_order.index(value)
  
    if value.isdigit():
        return int(value)
    return float('inf')

def sort_dynamic_list(data):
    return sorted(data, key=parse_range_or_size)

def set_apperal_category(root,  selected_id):
 
    namespace = {'svg': root.tag.split('}')[0].strip('{')}
    element = root.find(f".//svg:text[@id='{selected_id}']", namespace)
    
    if element is not None:       
        style = element.get("style", "")
        updated_style = ";".join([prop for prop in style.split(";") if not prop.strip().startswith("display")])
        if updated_style:
            element.set("style", updated_style)
        else:
            element.attrib.pop("style", None)
        print(f"Display removed for text element with ID '{selected_id}'.")
    else:
        print(f"No text element found with ID '{selected_id}'.")

def extract_sizes_from_xml_selected_tag(xmlroot):
   
    root = xmlroot

    name_attributes = ['IT', 'INT', 'EU', 'FR', 'USA / UK']
    sizes_dict = {}

    for name_attr in name_attributes:
        size_values = []
        for size in root.findall(f".//SizeChartItem/Size[@Name='{name_attr}']"):
            size_value = size.get("Value")
            if size_value and size_value not in size_values:
                size_values.append(size_value)
        sizes_dict[name_attr] = sorted(size_values)

    max_length = max((len(v) for v in sizes_dict.values()), default=0)

    table_array = []
    table_array.append(name_attributes)

    for i in range(max_length):
        row = [sizes_dict[key][i] if i < len(sizes_dict[key]) else "" for key in name_attributes]
        table_array.append(row)

    return table_array

def extract_sizes_from_xml_all_tag(XMLRoot):
        name_attributes=['ITA','ANNI-YEARS','MESI-MONTHS','YEARS','MONTHS','IT'] 
        sizes = []
        selected_size=''
        
        for name_attr in name_attributes:
            for size in XMLRoot.findall(f".//SizeChartItem/Size[@Name='{name_attr}']"):
                size_value = size.get("Value")
                if size_value and size_value not in sizes:
                        sizes.append(size_value)
        return sizes
def add_text_boxes_to_svg(root, size_array, selected_size, selected_size_style, unselected_size_style):
    
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)

    rect = root.find(".//*[@id='size_rect_selected']")
    if rect is None:
        print("Error: Rectangle with id 'size_rect' not found.")
        return

    rect_x = float(rect.attrib['x'])
    rect_y = float(rect.attrib['y'])
    rect_width = float(rect.attrib['width']) - 10
    rect_height = float(rect.attrib['height'])

    x_start = rect_x + 12  
    y_start = rect_y + 5 
    y_offset = 9
    num_columns = len(size_array[0])  

    text_group = ET.Element('g', {'id': 'size_text_group'})
    size_array = size_array[1:]

    for i, row in enumerate(size_array):  
        y_position = y_start + i * y_offset 
        if y_position > rect_y + rect_height - y_offset:
            break 

        is_selected = selected_size in row  # Corrected condition

        for j, value in enumerate(row):
            x_position = x_start + j * (rect_width / num_columns)  
            if j == num_columns - 1:
                x_position += 3
            if x_position > rect_x + rect_width:
                break   

            text_style = selected_size_style if is_selected else unselected_size_style          
            text_id = f'size_{i}_{j}'

            text_element = ET.Element('text', {
                'id': text_id,
                'transform': f'translate({x_position} {y_position})',               
                'text-anchor': 'middle',
                'style': text_style
            })

            tspan_element = ET.SubElement(text_element, 'tspan')
            tspan_element.text = value         
            text_group.append(text_element)

    root.append(text_group)
def set_code128_barcode(x, y, width, data, root):
    if width == '' or width is None:
        print("Ean 13 barcode width is not given")
        return
    generator = c128bc.BarcodeGenerator()
    barcodeno = data       
    x = float(x)      
    x = x - 10.5
    y = float(y)
    width = float(width)  
    width = width+1
    default_array = {
        "barcodeWidth": width,
        "barcodeHeight": 23,
        "color": 'cmyk(0,0,0,100)',
        "x": x,
        "y": y,
        "showCode": False,
        "inline": True,
        "barWidthRatio": 0.7,
        "quietZone": 10
    }
    svg_output = generator.getBarcodeSVG(barcodeno, "C128C", default_array)  
    directory = "barcode_svg"
    filename = f"{barcodeno}.svg"
    file_path = os.path.join(directory, filename)
    os.makedirs(directory, exist_ok=True)    
    
    with open(file_path, "w", encoding="utf-8") as file:
        file.write(svg_output)
    bars_content = get_rects_as_string(file_path) 
    bars_content = bars_content.strip()  

    if not bars_content:
        print("Error: No bars content")
        return {"error": "No bars content", "status_code": 400}

    try:
        bars_content = f'<svg xmlns="http://www.w3.org/2000/svg">{bars_content}</svg>'
        namespaces = {'ns0': 'http://www.w3.org/2000/svg'}       
        bars_element = ET.fromstring(bars_content)     
        barcodeArea = root.find(".//*[@id='Barcode_ean_128c']", namespaces)
        barcodeArea.clear()
        if barcodeArea is not None:         
            for elem in bars_element.iter():
                if '}' in elem.tag:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag.split('}')[1]}"
                else:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag}"
            barcodeArea.append(bars_element)
        else:
            print("No <rect> element found with id='barcode'.")
            return {"error": "No <rect> element found with id='barcode'.", "status_code": 404}
        return {"message": "SVG updated successfully"}

    except ET.ParseError as e:
        print( f"SVG parsing error: {str(e)}")
        return {"error": f"SVG parsing error: {str(e)}", "status_code": 500}
    finally:
               
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Temporary file {file_path} deleted.")


def size_append_circle(root,elementid,size_ranges, selected_size, variable_size_text_style, variable_size_box_style,variable_size_box_path_style):
   
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS) 
    rect_element = root.find(f".//*[@id='{elementid}']")
    if rect_element is None:
        raise ValueError(f"Rectangle with id '{elementid}' not found.")
    rect_x = float(rect_element.attrib["x"])
    rect_y = float(rect_element.attrib["y"])
    rect_width = float(rect_element.attrib["width"])
    rect_height = float(rect_element.attrib["height"])
    padding = 0
    usable_width = rect_width - 2 * padding
    usable_start_x = rect_x + padding
    row_start_y = rect_y + 1
    base_element_width = 10 
    base_alpha_element_width =9
    element_height = 10
    vertical_spacing = 2
    horizontal_spacing = 1.5
    size_count = len(size_ranges)
    all_alphabetic = all(label[0].isalpha() for label in size_ranges)  
    if size_count <= 5:
        columns = size_count
    elif size_count == 6 and all_alphabetic:
        columns = 6  
    elif size_count == 6:
        columns = 4
    elif size_count == 7:
        columns = 4
    elif size_count == 8:
        columns = 5
    elif size_count == 9:
        columns = 5
    else:
        columns = 5  

    rows = (size_count + columns - 1) // columns

    for row in range(rows):
        elements_in_row = min(columns, len(size_ranges) - row * columns)
        total_row_width = 0
        size_widths = []     
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
           
            element_width = base_alpha_element_width if label[0].isalpha() else base_element_width
            size_widths.append(element_width)
            total_row_width += element_width
        total_row_width += (elements_in_row - 1) * horizontal_spacing
        start_x = usable_start_x + (usable_width - total_row_width) / 2  
        
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
            element_width = base_alpha_element_width if label[0].isalpha() else base_element_width
            if label in ["XXL", "XXXL"]:
                element_width *= 2
            center_x = start_x + sum(size_widths[:col]) + col * horizontal_spacing + element_width / 2
            center_y = row_start_y + row * (element_height + vertical_spacing) + element_height / 2
            
            circle_style = f"{variable_size_box_path_style} display{':inline' if label == selected_size else ':none'} "
            if label in ["XXL", "XXXL"]:
                shape_element = ET.Element(
                    "ellipse",
                    {
                        "id": f"box_{label}",
                        "cx": str(center_x),
                        "cy": str(center_y-0.5),
                        "rx": str(element_width / 2),
                        "ry": str(element_height / 1.7),
                        "style": circle_style,
                    },
                )
            else:
                shape_element = ET.Element(
                    "circle",
                    {
                        "id": f"box_{label}",
                        "cx": str(center_x),
                        "cy": str(center_y-0.5),
                        "r": str(element_width / 2),
                        "style": circle_style,
                    },
                )
            root.append(shape_element)
            
            style_box = f"{variable_size_box_style} display{':inline' if label == selected_size else ':none'} "
            text_box_element = ET.Element(
                "text",
                {
                    "id": f"variable_Size_box_{label}",
                    "style": style_box, 
                    "transform": f"translate({center_x} {center_y})",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
            tspan_box_element = ET.SubElement(text_box_element, "tspan", {"x": "0", "y": "0"})
            tspan_box_element.text = label
            root.append(text_box_element)
            
            style_text = f"{variable_size_text_style} display{':none' if label == selected_size else ':inline'} "
            text_element = ET.Element(
                "text",
                {
                    "id": f"variable_Size_{label}",
                    "style": style_text,
                    "transform": f"translate({center_x} {center_y})",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
            tspan_element = ET.SubElement(text_element, "tspan", {"x": "0", "y": "0"})
            tspan_element.text = label
            root.append(text_element)
            
genProcess('customer_order_approval','B0608787')