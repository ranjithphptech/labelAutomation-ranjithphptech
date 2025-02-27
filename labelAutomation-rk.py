import os
import shutil
from db import conn
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import QName
from pathlib import Path
import configparser
from datetime import datetime
import re
from helpers import *
import ean13barcode as bc
import code128 as c128bc
from bs4 import BeautifulSoup
from pdf2image import convert_from_path
from fpdf import FPDF
current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
mandatoryIds = []
def genProcess(processName='',zipFile=''):
    baseNameOfZip = zipFile
    zipFile = zipFile+'.zip'
    config = configparser.ConfigParser()
    config.read('config.ini')
    orderProcessing = config['paths']['orderProcessing']
    orderOutputDir = config['paths']['orderOutputDir']
    svgDir = os.path.join('static',config['paths']['svgDir'])
    # customerApprovalPending = config['paths']['customerApprovalPending']
    failedOrders = config['paths']['failedOrders']
    currentZipFileName = baseNameOfZip
    currentZipOutputDir = ""
    try:
        print("process is going on "+zipFile)
        f = os.path.join(orderProcessing,zipFile)
        ordersData = {}
        with ZipFile(f,'r') as zObject:
            designCodes =[]
            currentZipOutputDir = orderOutputDir+"/"+baseNameOfZip
            Path(currentZipOutputDir).mkdir(parents=True, exist_ok=True)
            zObject.extractall(currentZipOutputDir)
            orderID = ""
            for xmlFile in Path(currentZipOutputDir).rglob('*.xml'):
                XMLDir = os.path.splitext(xmlFile)[0].replace(" ","_")
                xmlFilename =  os.path.basename(xmlFile).split('/')[-1]
                print("XML file name "+xmlFilename)
                xmlFileBasename = os.path.splitext(xmlFilename)[0]
                designCodes.append(xmlFileBasename)
                Path(XMLDir).mkdir(parents=True, exist_ok=True)
                xmlFileBasename = xmlFileBasename.replace(" ","_")
                XMLtree = ET.parse(xmlFile)
                XMLRoot = XMLtree.getroot()                    
               
                assetNameList = XMLRoot.find("./OrderItems/OrderItem/Asset/Name").text.split(",")
                product_code = XMLRoot.find("./OrderItems/OrderItem/Asset/Codes/Code").attrib['Value']
                
                if len(assetNameList)==2:
                    assetName = assetNameList[1]
                else:
                    assetName = assetNameList[0]
            
                assetName = assetName.strip() 
                
                dbcursor = conn.cursor(dictionary=True)
                dbcursor.execute("SELECT * FROM label_list WHERE label_name = '"+assetName+".svg' ")
                labelDet = dbcursor.fetchone()
                sizes_array = extract_sizes_from_xml(XMLRoot)
                
                
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
                else:
                    raise Exception('TAG not found , check tag list')
                
                mandatoryIds=[]
                selected_category = ""
                
                frontAssetName = assetName+"_FRONT"
                frontsvgString=svgDir+'/'+frontAssetName+'.svg'
                tagSno = 0
                tagGroups = {}
                latexSvgFiles =""
                              
                if os.path.isfile(frontsvgString):
                    namespaces = {node[0]: node[1] for _, node in ET.iterparse(frontsvgString, events=['start-ns'])}
                    for key, value in namespaces.items():
                        ET.register_namespace(key, value)
                    frontSVGtree = ET.parse(frontsvgString)
                    frontSvgRoot = frontSVGtree.getroot()  
                    tagGroups = {}
                    tagSno = 1
                    frontSvgName = '1.svg'
                    frontSvgFilePath = currentZipOutputDir+'/'+xmlFileBasename+'/'+frontSvgName
                
                if labelDet['dynamic']==1:                    
                    backAssetName = assetName+"_BACK"
                    backsvgString=svgDir+'/'+backAssetName+'.svg'
                    backSvgtree = ET.parse(backsvgString)
                    backSvgRoot = backSvgtree.getroot()  
                    
                    selling_price_position_style = get_selling_price_position(backSvgRoot)
                   
                    currency_india_style = selling_price_position_style.get('currency_india', {}).get('style', None)                 
                    currency_style = selling_price_position_style.get('currency', {}).get('style', None)
                    currency_y_position = selling_price_position_style.get('currency', {}).get('y_position', None)
                    selling_price_fraction_style = selling_price_position_style.get('selling_price_fraction', {}).get('style', None)
                    selling_price_fraction_y_position = selling_price_position_style.get('selling_price_fraction', {}).get('y_position', None)
                    selling_price_style = selling_price_position_style.get('selling_price', {}).get('style', None)
                    size_positions = get_size_position(backSvgRoot)
                    variable_size_text_style = size_positions.get('variable_size_text', {}).get('style', None)
                    variable_size_box_style = size_positions.get('variable_size_box', {}).get('style', None)
               
                    namespaces = {node[0]: node[1] for _, node in ET.iterparse(backsvgString, events=['start-ns'])}
                    for key, value in namespaces.items():
                        ET.register_namespace(key, value)
                   
                    supplierStype,country,color = '','',''
                    all_sizes=[] 
                    name_attributes=['ITA','ANNI-YEARS','MESI-MONTHS','YEARS','MONTHS','IT'] 
                    sizes = []
                    selected_size=''
                    
                    for name_attr in name_attributes:
                        for size in XMLRoot.findall(f".//SizeChartItem/Size[@Name='{name_attr}']"):
                            size_value = size.get("Value")
                            if size_value and size_value not in sizes:
                                    sizes.append(size_value)
                        
                    all_sizes = sizes
                    
                    items = XMLRoot.findall("./OrderItems/OrderItem/Item")
                    
                    if len(items)>1:
                        labelRatio = '0.5'
                    else:
                        labelRatio = '0.5'
                        
                    season_code =""
                    for item in items:
                        mandatoryIds = ['quantity']
                        SVGtree = ET.parse(backsvgString)
                        SVGroot = SVGtree.getroot()
                        itemID = item.find('./ItemID').text
                        qty = item.find('./Quantity').text  
                        status = set_svg_text(SVGroot, 'quantity', f"Qty - {qty}")
                        if status==False:
                            raise Exception("Sorry, not found in svg image "+itemID)
                        selling_price= 0
                        selling_price_fraction=00
                        outPutSvgName = itemID+"_"+str(tagSno)+'.svg'
                        currentSvgFilePath=currentZipOutputDir+'/'+xmlFileBasename+'/'+outPutSvgName
                        selected_name_attr =''
                        code128_barcode=''
                        currency=''
                      
                        for size in item.findall("./SizeChartItem/Size"):
                            nameAttr = size.attrib['Name'].replace(' ', '_')
                            nameAttr = re.sub(r'[-_]+', '-', nameAttr).strip('-') 
                            
                            if nameAttr=='ANNI-YEARS' or nameAttr=='MONTHS' or nameAttr=='YEARS':
                                if(nameAttr=='ANNI-YEARS' or nameAttr=='YEARS' or nameAttr=="MONTHS"):
                                        selected_size=size.attrib['Value'] 
                                        selected_name_attr=nameAttr                                    
                                set_svg_text(SVGroot, 'Age_Text', nameAttr)  
                                set_svg_text(SVGroot, 'Size_MONTHS_OR_YEAR', size.attrib['Value'])     
                                set_svg_text(SVGroot, 'ANNI-YEARS', size.attrib['Value'])
                                set_svg_text(SVGroot, 'YEARS', size.attrib['Value'])
                                set_svg_text(SVGroot, 'MONTHS', size.attrib['Value'])
                                
                            elif nameAttr=='CM' :
                                set_svg_text(SVGroot, nameAttr, size.attrib['Value'])
                                set_svg_text(SVGroot, f'size_{nameAttr}', size.attrib['Value'])
                                set_svg_text(SVGroot, 'unit_text', nameAttr)                       
                            
                            else:
                                set_svg_text(SVGroot, nameAttr, size.attrib['Value'])
                                if(nameAttr=='ITA' or nameAttr=='IT' or nameAttr=='INT' ):
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
                                print(country)
                                
                            if variable.attrib['Question']=='Color':
                                tag_color = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'tag_color', tag_color)
                                
                            if variable.attrib['Question']=='Style Code':
                                styleCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'style_code', styleCode)
                                 
                            if variable.attrib['Question']=='Material(Model Code)':
                                material_model_code = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'material_model_code', material_model_code)


                            # if variable.attrib['Question']=='Article name':
                            #     article_name = variable.find("./Answer/AnswerValues/AnswerValue").text
                            #     set_svg_text(SVGroot, 'article_name', article_name)

                            if variable.attrib['Question']=='Color Code':
                                colorCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'color_code', colorCode)
                            
                            if variable.attrib['Question']=='Supplier Style':
                                supplierStype = variable.find("./Answer/AnswerValues/AnswerValue").text              
                                
                            if variable.attrib['Question']=='Translation Code':
                                translations = variable.findall("./Answer/AnswerValues/AnswerValue")
                                for translation in translations:
                                    lang = translation.attrib['Name']                      
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

                            if variable.attrib['Question']=='Sub Department':
                                subdepartment = variable.find("./Answer/AnswerValues/AnswerValue").text
                                set_svg_text(SVGroot, 'sub_department', subdepartment)                           
                                
                            if variable.attrib['Question']=='Barcode Number':
                                barcodenumber = variable.find("./Answer/AnswerValues/AnswerValue").text
                                data=barcodenumber
                                bar1 = barcodenumber[0] 
                                bar2 = barcodenumber[1:7]
                                bar3 = barcodenumber[7:]
                                bar_values = {'bar1': bar1,'bar2': bar2,'bar3': bar3 }
                                
                                for bar_id, bar_text in bar_values.items():
                                    set_svg_text(SVGroot, f'{bar_id}', bar_text)

                                barcodeArea = SVGroot.find(".//*[@id='Barcode']")
                                for rect in barcodeArea:
                                    labelDet['barcode_x_position'] = rect.attrib['x']
                                    labelDet['barcode_y_position'] = rect.attrib['y']
                                    break
                        
                            if variable.attrib['Question']=='EAN 128C':
                                code128_barcodenumber = variable.find("./Answer/AnswerValues/AnswerValue").text
                                code128_barcode=code128_barcodenumber
                                set_svg_text(SVGroot, 'ean_128c', code128_barcode)
                              

                                code128_barcodeArea = SVGroot.find(".//*[@id='Barcode_ean_128c']")
                                for rect in code128_barcodeArea:
                                    labelDet['code128_barcode_x_position'] = rect.attrib['x']
                                    labelDet['code128_barcode_y_position'] = rect.attrib['y']
                                    break                                  
            
                        if selected_category !='':
                            set_category(SVGroot,selected_category)  
                        else:
                            set_category(SVGroot,selected_name_attr)
                        
                        tagGroups.setdefault(country, {}).setdefault(color, {}).setdefault(supplierStype, {}).setdefault('tagList',[]).append(outPutSvgName)
                       
                       
                        set_barcode(labelDet['barcode_x_position'],labelDet['barcode_y_position'],67,data,SVGroot)
                       
                        if code128_barcode !='':
                            set_code128_barcode(labelDet['code128_barcode_x_position'],labelDet['code128_barcode_y_position'],labelDet['barcode_width'],code128_barcode,SVGroot)
                            int_order = ['XS', 'S', 'M', 'L', 'XL', 'XXL','3XL','XXXL','4XL']
                            int_rank = {size: index for index, size in enumerate(int_order)}
                            int_index = sizes_array[0].index('INT')
                            sorted_array = [sizes_array[0]] + sorted(
                                sizes_array[1:], key=lambda x: int_rank.get(x[int_index], float('inf'))
                            )
                            add_text_boxes_to_svg(SVGroot, sorted_array, selected_size,variable_size_box_style, variable_size_text_style)
                        else:
                            size_order= sort_dynamic_list(all_sizes)
                            size_append(SVGroot,size_order,selected_size,variable_size_text_style,variable_size_box_style)
                        
                        if currency !='':
                            if currency=="₹":           
                                selling_price_append(SVGroot,currency,selling_price,selling_price_fraction,currency_y_position,selling_price_fraction_y_position,currency_india_style,selling_price_fraction_style,selling_price_style)
                            else:
                                selling_price_append(SVGroot,currency,selling_price,selling_price_fraction,currency_y_position,selling_price_fraction_y_position,currency_style,selling_price_fraction_style,selling_price_style)
                        set_apperal_category(SVGroot, selected_category)  
                        SVGtree.write(currentSvgFilePath,encoding='utf-8', xml_declaration=True)
                     
                        #add_background_to_svg(currentSvgFilePath,'/home/ranjith/Art_work_automation/Sainmarknewlogo.png')
                        #svg file generation end of xml file end
                        tagSno +=1
                
                    if season_code!="":
                        set_svg_text(frontSvgRoot,"season_code","("+str(season_code)+")")
                    if os.path.isfile(frontsvgString):
                        frontSVGtree.write(frontSvgFilePath)
                        
                    font_families = extract_font_families_from_style(currentSvgFilePath)
                    print (f"font Familes : {font_families}")
                    width, height = get_svg_dimensions(currentSvgFilePath)
                    print (f"svg width : {width} svg height :{height}")              
                   
                    isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                    if isPDFOutputDir==False:
                        Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
            
                    title = supplierStype+" - "+country+" - "+color+" - "+orderID
                    buyerTxt         = '               OVS'
                    submittedDateTxt = createdDate
                    
                    pdfFileName = (assetName+"_"+baseNameOfZip).replace(" ","_")
                    latexFileName = pdfFileName
                    latexFilePath = Path(currentZipOutputDir) / "pdf" / f"{latexFileName}.tex"
                    latexFile = Path(latexFilePath)
                    latexFile.touch(exist_ok= True)
                    graphicspath = currentZipOutputDir+'/'+xmlFileBasename
                 
                    latexSvgFiles = ""
                    svg_dir = Path(currentZipOutputDir) / xmlFileBasename
                    pdfPageBody =""
                    latexFonts = ""
           


                    print("Generated latexFonts:\n", latexFonts)
                    # Iterate over tagGroups to create pages
                    for country, colorGroups in tagGroups.items():
                        for color, supplierGroups in colorGroups.items():
                            for supplierStyle, tagData in supplierGroups.items():                
                                tagList = tagData.get('tagList', [])
                                title = supplierStyle+" - "+country+" - "+color+" - "+orderID
                                              
                                pdfPageBody += r'''\begin{table}
                                    \begin{tabularx}{1\textwidth}{|*{7}{Y|}}
                                    \hline 
                                        \multirow{2}{=}{ \begin{center} \includegraphics[height=1.6cm,width=3.9cm]{Sainmarknewlogo} \end{center} } 
                                        &\multicolumn{3}{|p{10cm}|}{BUYER : '''+buyerTxt+r'''}  &\multirow{2}{=}{  \begin{center} ARTWORK\\ FOR\\ APPROVAL \end{center}} \\
                                    \cline{2-4}
                                        &\multicolumn{3}{l|}{CUSTOMER : '''+customerName+r'''} &\\
                                    \cline{2-4}
                                        &\multicolumn{3}{l|}{DESIGN CODE : '''+assetName+r'''} &\\ 
                                    \cline{2-4}
                                        &\multicolumn{3}{l|}{PRODUCT CODE : '''+product_code+r'''} &\\
                                    \cline{2-4}
                                        &\multicolumn{3}{l|}{SUBMITTED DATE : '''+submittedDateTxt+r'''} &\\
                                    \cline{2-4}
                                        &\multicolumn{3}{l|}{} &\\
                                    \hline
                                    \end{tabularx}
                                    \end{table}
                                    \begin{center}
                                    {\Large \textbf{\textcolor{red}{'''+title+r'''}}}
                                    \end{center}
                                    \hfill\break
                                    \centering '''
                        
                                latexSvgFilesCode =''
                                if os.path.isfile(frontsvgString):
                                    front_svg_path = Path(currentZipOutputDir) / xmlFileBasename / frontSvgName
                                    frontSvgBaseName = os.path.splitext(frontSvgName)[0]
                                    width, height = get_svg_dimensions(front_svg_path)                                
                                    latexSvgFilesCode =f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{frontSvgBaseName}}} \n'   
                                for tag in tagList:
                                    svg_path = Path(currentZipOutputDir) / xmlFileBasename / tag
                                    baseNameSVG = os.path.splitext(tag)[0]
                                    width, height = get_svg_dimensions(svg_path)
                                    print(title+"-"+baseNameSVG)
                                    latexSvgFilesCode +=f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{baseNameSVG}}} \n'   
                                pdfPageBody += latexSvgFilesCode+"\n\\newpage"
                    latexFonts=""
                    for font in font_families:
                        if font in ["Arial MT"]:
                            continue  # Skip these fonts

                        sanitized_font = sanitize_latex_string(font.replace(' ', '').replace('-', ''))
                        try:
                            latexFonts += "\\IfFontExistsTF{" + font + "}{\\newfontfamily\\" + sanitized_font + "{" + font + "}}" + "{\\textbf{Warning: Font " + font + " not found.}}\n"
                        except Exception as e:
                            print(f"Warning: Error processing font '{font}': {e}")
                            pass
                        
                    with open(latexFilePath, 'w') as clatexFile:
                        final_latex = r'''\documentclass{article}
                        \usepackage{multirow,tabularx}
                        \usepackage{graphicx}
                        \usepackage[export]{adjustbox}
                        \usepackage{xcolor}
                        \usepackage[inkscapelatex=false]{svg}
                        \usepackage[a3paper,landscape,left=5mm,right=5mm,bottom=5mm]{geometry}
                        \setlength{\voffset}{-0.75in}
                        \setlength{\headsep}{5pt}
                        \usepackage{layout}
                        \usepackage{fontspec}
                        \newcolumntype{Y}{>{\centering\arraybackslash}X}
                        \renewcommand{\arraystretch}{1.2}
                        \graphicspath{{''' + graphicspath + r'''}}
                        ''' + latexFonts + r'''
                        \begin{document}
                        ''' + pdfPageBody + r'''
                        \end{document}'''

                        print("Final LaTeX Output:\n", final_latex)  # Debugging
                        clatexFile.write(final_latex)
                    # with open(latexFilePath,'w') as clatexFile:
                    #     clatexFile.write(r'''\documentclass{article}
                    #         \usepackage{multirow,tabularx}
                    #         \usepackage{graphicx}
                    #         \usepackage[export]{adjustbox}
                    #         \usepackage{xcolor}
                    #         \usepackage[inkscapelatex=false]{svg}
                    #         \usepackage[a3paper,landscape,left=5mm,right=5mm,bottom=5mm]{geometry}
                    #         %\usepackage[b2paper,landscape,left=5mm,right=5mm,bottom=5mm]{geometry}
                    #         \setlength{\voffset}{-0.75in}
                    #         \setlength{\headsep}{5pt}
                    #         \usepackage{layout}
                    #         \usepackage{fontspec}
                    #         \newcolumntype{Y}{>{\centering\arraybackslash}X}
                    #         \renewcommand{\arraystretch}{1.2}
                    #         \graphicspath{{'''+graphicspath+r'''}}
                    #         %\IfFontExistsTF{Arial-Bold}{\newfontfamily\Arial{Arial}}{\textbf{Warning: Font Arial not found.}}
                    #         '''+latexFonts+r'''
                    #         \begin{document}
                    #         '''+pdfPageBody+r'''
                    #         \end{document} ''')
                    
                         
                
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
                    
                    font_families = extract_font_families_from_style(currentSvgFilePath)
                    print (f"font Familes : {font_families}")
                    width, height = get_svg_dimensions(currentSvgFilePath)
                    print (f"svg width : {width} svg height :{height}")
                    
                    isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                    if isPDFOutputDir==False:
                        Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                
                    title = supplierStype+" - "+country+" - "+orderID
                    buyerTxt         = '               OVS'
                    submittedDateTxt = createdDate
                    
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
                            latexSvgFiles +=f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{baseNameSVG}}} \n'             
                    with open(latexFilePath,'w') as clatexFile:
                        clatexFile.write(r'''\documentclass{article}
                            \usepackage{multirow,tabularx}
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
                            \begin{table}
                            \begin{tabularx}{1\textwidth}{|*{7}{Y|}}
                            \hline 
                                \multirow{2}{=}{ \begin{center} \includegraphics[height=1.7cm,width=3.9cm]{Sainmarknewlogo} \end{center} } 
                                &\multicolumn{3}{|p{10cm}|}{BUYER : '''+buyerTxt+r'''}  &\multirow{2}{=}{  \begin{center} ARTWORK\\ FOR\\ APPROVAL \end{center}} \\
                            \cline{2-4}
                                &\multicolumn{3}{l|}{CUSTOMER : '''+customerName+r'''} &\\
                            \cline{2-4}
                                &\multicolumn{3}{l|}{DESIGN CODE : '''+assetName+r'''} &\\ 
                            \cline{2-4}
                                &\multicolumn{3}{l|}{PRODUCT CODE : '''+product_code+r'''} &\\
                            \cline{2-4}
                                &\multicolumn{3}{l|}{SUBMITTED DATE : '''+submittedDateTxt+r'''} &\\
                            \cline{2-4}
                                &\multicolumn{3}{l|}{} &\\
                            \hline
                            \end{tabularx}
                            \end{table}
                            \begin{center}
                            {\Large \textbf{\fontspec{Arial-Bold}\textcolor{red}{'''+title+r'''}}}
                            \end{center}
                            \hfill\break
                            \centering 
                            '''+latexSvgFiles+r'''
                            \end{document} ''')
                                  
                    #static tag latex creation end
                    
                latexFilePathStr = current_dir+"/"+str(latexFilePath)
                outputDirStr = current_dir+"/"+str(Path(currentZipOutputDir) / "pdf")   
                
                # print(f'xelatex --shell-escape --enable-write18 --output-directory="{outputDirStr}" "{latexFilePathStr}"')
                # exit()
                x = os.system(f'xelatex --shell-escape --enable-write18 --output-directory="{outputDirStr}" "{latexFilePathStr}"')
                reduce_pdf_quality(f'{outputDirStr}/{pdfFileName}.pdf',f'{outputDirStr}/{pdfFileName}_compressed.pdf')
                # os.remove(f'{outputDirStr}/{pdfFileName}.pdf')
           
            for x in ordersData:
                submitted_date = datetime.strptime(ordersData.get(x).get('createdDate'),'%d/%m/%Y %H:%M').date()
                toemail = ordersData.get(x).get('customerEmail')
                approval_mail_status = 'P'
                dbcursor = conn.cursor()
                dbcursor.execute("INSERT INTO orders(order_id, buyer, customer_id,customer_name, customer_email_id,approval_mail_status, design_codes, submitted_date,status, created_date_time) VALUES('"+x+"', 'OVS','"+ordersData.get(x).get('customerID')+"', '"+ordersData.get(x).get('customerName')+"', '"+ordersData.get(x).get('customerEmail')+"','"+approval_mail_status+"', '"+(",".join(designCodes))+"', '"+str(submitted_date)+"', 'CAP', '"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"');")
                conn.commit()
                    
            print('mail triggered')
            exit()
            res = send_mail(subject='Subject',toMailid=toemail,attachmentPath=currentZipOutputDir+'/pdf')
            if res['status']=='success':
                approval_mail_status = 'S'
                shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', customerApprovalPending+'/'+baseNameOfZip+'.zip')
            else:
                approval_mail_status = 'F'
                shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', failedOrders+'/'+baseNameOfZip+'.zip')
                dbcursor = conn.cursor()
                dbcursor.execute("INSERT INTO failed_orders(order_id,error,status,created_date_time) VALUES('"+currentZipFileName+"','"+res['msg']+"','F','"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"')")
                conn.commit()
            
            delete_folder_and_files(currentZipOutputDir)
            delete_folder_contents_only('svg-inkscape')
                
    except Exception as error:

        print(f"Error - {error}")       
        # shutil.move(orderProcessing+'/'+baseNameOfZip+'.zip', failedOrders+'/'+baseNameOfZip+'.zip')  
        # delete_folder_and_files(currentZipOutputDir)
        # dbcursor = conn.cursor()
        # dbcursor.execute("INSERT INTO failed_orders(order_id,error,status,created_date_time) VALUES('"+currentZipFileName+"','"+str(format(error)).replace("'",'"').strip()+"','F','"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"')")
        # conn.commit()

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
        print(f"ID '{element_id}' not found in SVG.")

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

def set_code128_barcode(x, y, width, data, root):
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


def extract_sizes_from_xml(xmlroot):
   
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

def add_text_boxes_to_svg(root, size_array, selected_size, selected_size_style, unselected_size_style):
    
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)

    rect = root.find(".//*[@id='size_rect']")
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
    horizontal_spacing = 7.5
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
            rect_x = start_x + sum(size_widths[:col]) + col * horizontal_spacing
            rect_y = row_start_y + row * (element_height + vertical_spacing)
            text_x = rect_x + element_width / 2
            text_y = rect_y + element_height / 2
            
            rect_element = ET.Element(
                "rect",
                {
                    "id": f"box_{label}",
                    "x": str(rect_x - 3),
                    "y": str(rect_y - 0.5),
                    "width": str(element_width + 6),
                    "height": str(element_height),
                    "style": "display:inline" if label == selected_size else "display:none",
                },
            )
            root.append(rect_element)
            style_box = f"{variable_size_box_style} display{':inline' if label == selected_size else ':none'} "
            text_box_element = ET.Element(
                "text",
                {
                    "id": f"variable_Size_box_{label}",
                    "style":style_box, 
                    "transform": f"translate({text_x} {text_y})",
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
                    "transform": f"translate({text_x} {text_y})",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
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
        style_content = style_tag.get_text()  # Use .get_text() instead of .string
        font_matches = re.findall(r'font-family:\s*([^;]+);', style_content)
        for font in font_matches:
            clean_fonts = [f.strip().strip("'\"") for f in font.split(',')]
            font_families.update(clean_fonts)

   
    for element in soup.find_all(style=True):
        style_content = element['style']
        font_matches = re.findall(r'font-family:\s*([^;]+);', style_content)
        for font in font_matches:
            clean_fonts = [f.strip().strip("'\"") for f in font.split(',')]
            font_families.update(clean_fonts)

    return list(font_families)


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
    
   

    return size_positions

# selling price and currency value updated in svg
def selling_price_append(root, currency_symbol,selling_price,selling_price_fraction_part,currency_y_position, selling_price_y_position, currency_style, selling_price_fraction_style,selling_price_style):
    if selling_price == "0":
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
def sanitize_latex_string(s):   
    return s.replace('#', '\\#').replace('$', '\\$').replace('%', '\\%').replace('_', '\\_')
 
genProcess('customer_order_approval','B0559934')