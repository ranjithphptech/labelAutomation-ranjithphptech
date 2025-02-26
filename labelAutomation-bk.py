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
from bs4 import BeautifulSoup

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)

def genProcess(processName='',zipFile=''):
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
                # xmlFilename = os.path.basename(xmlFile).split('/')[-1].replace(' ', '_') 
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
                
                dynamicLabel = 'no'             
           
                category_id=labelDet['tag_category']
                category_List=[]
                selected_category =""

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
                    positions_and_classes = get_svg_positions_and_classes(svgString)
                currency_class = positions_and_classes.get('currency', {}).get('class', None)
                currency_y_position = positions_and_classes.get('currency', {}).get('y_position', None)
                selling_price_fraction_class = positions_and_classes.get('selling_price_fraction', {}).get('class', None)
                selling_price_fraction_y_position = positions_and_classes.get('selling_price_fraction', {}).get('y_position', None)
                variable_size_text_class = positions_and_classes.get('variable_size_text', {}).get('class', None)
                variable_size_box_class = positions_and_classes.get('variable_size_box', {}).get('class', None)
                namespaces = {node[0]: node[1] for _, node in ET.iterparse(svgString, events=['start-ns'])}
                for key, value in namespaces.items():
                    ET.register_namespace(key, value)
            
                items = XMLRoot.findall("./OrderItems/OrderItem/Item")
                if len(items)>1:
                    labelRatio = '0.5'
                else:
                    labelRatio = '0.5'
                
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
                print(f"sizes {all_sizes}")

                for item in items:
                    SVGtree = ET.parse(svgString)
                    SVGroot = SVGtree.getroot()
                    itemID = item.find('./ItemID').text
                    qty = item.find('./Quantity').text  
                    set_svg_text(SVGroot, 'quantity', f"Qty-{qty}")
                    selling_price= 0
                    selling_price_fraction=00
                    svgfilepath=currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg'
                    currency_symbol=""
                        
                    for size in item.findall("./SizeChartItem/Size"):
                        nameAttr = size.attrib['Name'].replace(' ', '_')
                        nameAttr = re.sub(r'[-_]+', '-', nameAttr).strip('-') 
                        if nameAttr=='ANNI-YEARS' or nameAttr=='MONTHS' or nameAttr=='YEARS':
                            if(nameAttr=='ANNI-YEARS' or nameAttr=='YEARS' or nameAttr=="MONTHS"):
                                    selected_size=size.attrib['Value']                                    
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
                            if(nameAttr=='ITA' or nameAttr=='IT'):
                                selected_size=size.attrib['Value']
                               
                            if(nameAttr=='MESI-MONTHS'):
                                selected_size=size.attrib['Value']
                                   
                    itemVariables = item.findall('./Variables/Variable')
                
                    for variable in itemVariables:

                        if variable.attrib['Question']=='Currency':
                            currency = variable.findall("./Answer/AnswerValues/AnswerValue")

                            for curr in currency:
                                currency_name = curr.attrib['Name']                            

                                if(currency_name=='Symbol'):
                                    currency= curr.text 
                                    currency_symbol=curr.text                                                
                                                            
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
                            color = variable.find("./Answer/AnswerValues/AnswerValue").text
                            
                        if variable.attrib['Question']=='Style Code':
                            styleCode = variable.find("./Answer/AnswerValues/AnswerValue").text
                            set_svg_text(SVGroot, 'style_code', styleCode)
                        
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
                            SVGtree.write(currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg')  
                            for bar_id, bar_text in bar_values.items():
                                set_svg_text(SVGroot, f'{bar_id}', bar_text)                        

                    SVGtree.write(currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg')                  
                    barcode_append(labelDet['barcode_x_position'],labelDet['barcode_y_position'],labelDet['barcode_width'],data,svgfilepath)                        
                    set_category(svgfilepath,selected_category)  
                    size_order= sort_dynamic_list(all_sizes)
                    size_append(svgfilepath,size_order,selected_size,variable_size_text_class,variable_size_box_class)                    
                    selling_price_append(svgfilepath,currency,selling_price,selling_price_fraction,currency_y_position,selling_price_fraction_y_position,currency_class,selling_price_fraction_class) 
                          
            
                font_families = extract_font_families_from_style(svgString)
                print (f"font Familes : {font_families}")
                width, height = get_svg_dimensions(svgString)
                print (f"svg width : {width} svg height :{height}")
               
                isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                if isPDFOutputDir==False:
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                if dynamicLabel=='no':
                    title = assetName+" - "+orderID
                else:
                    title = supplierStype+" - "+country+" - "+color+" - "+orderID
                buyerTxt         = 'BUYER               : OVS'
                submittedDateTxt = createdDate
                
                latexFilePath = Path(currentZipOutputDir) / "pdf" / f"{assetName}_{baseNameofZip}.tex"
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
                for font in font_families:
                    sanitized_font = sanitize_latex_string(font.replace(' ', '').replace('-', ''))
                    try:                       
                         clatexFile.write(f'\\IfFontExistsTF{{{font}}}'f'{{\\newfontfamily\\{sanitized_font}{{{font}}}}}' f'{{\\textbf{{Warning: Font {font} not found.}}}}\n')
                    except Exception as e:
                        print(f"Warning: Error processing font '{font}': {e}")
                        exit()
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
                clatexFile.write('\\color{red} \Large\n')
                clatexFile.write('\\textbf{'+title+'}\n')
                clatexFile.write('\\end{center}\n')
                clatexFile.write('\\hfill\\break\n')
                clatexFile.write('\\centering\n')                

                print(currentZipOutputDir+'/'+xmlFileBasename)              
                for svg in os.listdir(Path(currentZipOutputDir) / xmlFileBasename):
                        if svg.endswith(".svg"):
                            svg_path = Path(currentZipOutputDir) / xmlFileBasename / svg
                            baseNameSVG = os.path.splitext(svg)[0]
                            width, height = get_svg_dimensions(svg_path)
                            print(f"width : {width}   height : {height}")                                                   
                            clatexFile.write(f'\\includesvg[inkscapearea=page, width={width:.2f}mm, height={height:.2f}mm]{{{baseNameSVG}}} \n')
                    
                clatexFile.write('\\end{document}\n')
                clatexFile.close()   
                latexFilePathStr = str(latexFilePath)
                outputDirStr = str(Path(currentZipOutputDir) / "pdf")   
                
                x = os.system(f'xelatex "{latexFilePathStr}" --output-directory="{outputDirStr}" --shell-escape --enable-write18')
                          
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
        res = send_mail(subject='Subject',toMailid='krishnaveni@indsysholdings.com',attachmentPath=currentZipOutputDir+'/pdf')
        
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

def sanitize_latex_string(s):   
    return s.replace('#', '\\#').replace('$', '\\$').replace('%', '\\%').replace('_', '\\_')

def set_svg_text(svg_root, element_id, text_value):
    elements = svg_root.findall(f".//*[@id='{element_id}']")
    
    if elements:
       for element in elements:
            if element.text is not None:
                element.text = text_value
            else:
                element.text = text_value
    else:
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
    
def barcode_append(x, y, width, data, svgfile):
    print(f"Received data: {data}, x: {x}, y: {y}, width: {width} , svg file path: {svgfile}")
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

    svgPath = svgfile
   
    try:
        bars_content = f'<svg xmlns="http://www.w3.org/2000/svg">{bars_content}</svg>'
        tree = ET.parse(svgPath)
        root = tree.getroot()      
        namespaces = {'ns0': 'http://www.w3.org/2000/svg'}       
        bars_element = ET.fromstring(bars_content)     
        target_rect = root.find(".//*[@id='Barcode']", namespaces)
        
        if target_rect is not None:             
          
            for elem in bars_element.iter():
                
                if '}' in elem.tag:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag.split('}')[1]}"
                else:
                    elem.tag = f"{{http://www.w3.org/2000/svg}}{elem.tag}"

            # Append the new barcode
            target_rect.append(bars_element)
        else:
            print("No <rect> element found with id='barcode'.")
            return {"error": "No <rect> element found with id='barcode'.", "status_code": 404}

        # Write the modified SVG back to the file
        tree.write(svgPath, encoding='utf-8', xml_declaration=True)
        return {"message": "SVG updated successfully", "output_path": svgPath}

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

def size_append(svg_file, size_ranges, selected_size, variable_size_text_class, variable_size_box_class):
    tree = ET.parse(svg_file)
    root = tree.getroot()
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
    usable_start_x = rect_x + padding +3
    row_start_y = rect_y + padding + 4
    usable_height = rect_height - 2 * padding
  
    base_element_width = 12.5  
    base_alpha_element_width = 6.5  
    element_height = 8.5
    vertical_spacing = 2
    columns = 5

    rows = (len(size_ranges) + columns - 1) // columns
    total_required_height = rows * (element_height + vertical_spacing)

    for row in range(rows):
        elements_in_row = min(columns, len(size_ranges) - row * columns)
       
        total_row_width = 0
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
            if label[0].isalpha():
                total_row_width += base_alpha_element_width
            else:
                total_row_width += base_element_width

        total_row_width += (elements_in_row - 1) * 10  
 
        start_x = usable_start_x + (usable_width - total_row_width) / 2
       
        for col in range(elements_in_row):
            index = row * columns + col
            label = size_ranges[index]
          
            if label[0].isalpha():
                element_width = base_alpha_element_width
                horizontal_spacing = 7
            else:
                element_width = base_element_width
                horizontal_spacing = 8

           
            rect_x = start_x + col * (element_width + horizontal_spacing)
            rect_y = row_start_y + row * (element_height + vertical_spacing)
            text_x = rect_x + element_width / 2
            text_y = rect_y + element_height / 2
            box_y = text_y
            rect_box_y = rect_y

         
            rect_element = ET.Element(
                "rect",
                {
                    "id": f"box_{label}",
                    "x": str(rect_x - 3),
                    "y": str(rect_box_y - 0.5),
                    "width": str(element_width + 6),
                    "height": str(element_height),
                },
            )
            rect_element.set(
                QName(SVG_NS, "style"), "display:inline" if label == selected_size else "display:none"
            )
            root.append(rect_element)

          
            text_box_element = ET.Element(
                "text",
                {
                    "id": f"variable_Size_box_{label}",
                    "class": variable_size_box_class,
                    "transform": f"translate({text_x} {box_y})",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
            tspan_box_element = ET.SubElement(text_box_element, "tspan", {"x": "0", "y": "0"})
            tspan_box_element.text = label
            text_box_element.set(
                QName(SVG_NS, "style"), "display:inline" if label == selected_size else "display:none"
            )
            root.append(text_box_element)

           
            text_element = ET.Element(
                "text",
                {
                    "id": f"variable_Size_{label}",
                    "class": variable_size_text_class,
                    "transform": f"translate({text_x} {text_y})",
                    "text-anchor": "middle",
                    "dominant-baseline": "middle",
                },
            )
            tspan_element = ET.SubElement(text_element, "tspan", {"x": "0", "y": "0"})
            tspan_element.text = label
            root.append(text_element)

           
            if label == selected_size:
                text_box_element.set(QName(SVG_NS, "style"), "display:inline")
            else:
                text_box_element.set(QName(SVG_NS, "style"), "display:none")
            root.append(text_box_element)


    tree.write(svg_file, xml_declaration=True, encoding="utf-8")


def set_category(input_svg,selected_category):  
    tree = ET.parse(input_svg)
    root = tree.getroot()
    namespace = {'svg': 'http://www.w3.org/2000/svg'}
    selected_element = root.find(f".//svg:g[@id='{selected_category}']", namespace)
    if selected_element is not None:
        selected_element.attrib.pop('display', None) 
        print(f"Element with ID '{selected_category}' is now visible.")
    else:
        print(f"No element found with ID '{selected_category}'.")

    tree.write(input_svg)
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
def extract_transform_and_class(element):
        transform = element.attrib.get('transform', '')
        class_attr = element.attrib.get('class', '')
        y_position = None
        if transform:           
            match = re.search(r'translate\(([-\d.]+)[, ]+([-\d.]+)\)', transform)
            if match:               
                x_position = match.group(1)  
                y_position = match.group(2)  
        return y_position, class_attr

# get extract class from currency and translate y position in array element
def get_svg_positions_and_classes(svg_file):  
    tree = ET.parse(svg_file)
    root = tree.getroot()   
    SVG_NS = "{http://www.w3.org/2000/svg}"
    positions_and_classes = {}   
   
    currency_element = root.find(".//" + SVG_NS + "text[@id='currency']")
    if currency_element is not None:
        y_position, class_attr = extract_transform_and_class(currency_element)
        positions_and_classes['currency'] = {'y_position': y_position, 'class': class_attr}
    
    selling_price_fraction_element = root.find(".//" + SVG_NS + "text[@id='selling_price_fraction']")
    if selling_price_fraction_element is not None:
        y_position, class_attr = extract_transform_and_class(selling_price_fraction_element)
        positions_and_classes['selling_price_fraction'] = {'y_position': y_position, 'class': class_attr}
    
    variable_size_text_element = root.find(".//" + SVG_NS + "text[@id='variable_size_text']")
    if variable_size_text_element is not None:
        y_position, class_attr = extract_transform_and_class(variable_size_text_element)
        positions_and_classes['variable_size_text'] = {'y_position': y_position, 'class': class_attr}

    variable_size_box_element = root.find(".//" + SVG_NS + "text[@id='variable_size_box']")
    if variable_size_box_element is not None:
        y_position, class_attr = extract_transform_and_class(variable_size_box_element)
        positions_and_classes['variable_size_box'] = {'y_position': y_position, 'class': class_attr}

    return positions_and_classes
# selling price and currency value updated in svg
def selling_price_append(svg_file, currency_symbol,selling_price,selling_price_fraction_part,currency_y_position, selling_price_y_position, currency_class, selling_price_fraction_class):
    if selling_price == "0":
        return    
    tree = ET.parse(svg_file)
    root = tree.getroot()   
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)
   
    viewBox = root.attrib.get("viewBox", "0 0 100 100").split()
    svg_width = float(viewBox[2])
    print(f"svg_width: {svg_width}")
    char_widths = {
        "0": 9.5, "1": 5.0, "2": 9.5, "3": 9.5, "4": 9.5,
        "5": 9.5, "6": 9.5, "7": 9.5, "8": 9.5, "9": 9.5
    }
    default_char_width = 11.5
    char_width = 9.5
    spacing = 5 
    if currency_symbol=="₹":
        spacing = 9 
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
            "id": "CurrencySymbol",
            "class": currency_class,
            "transform": f"translate({currency_x_position} {currency_y_position} )",
        })
        tspan_currency = ET.SubElement(currency_element, "tspan", {"x": "0", "y": "0"})
        tspan_currency.text = f"{currency_symbol} {selling_price } "
        root.append(currency_element)
        decimal_element = ET.Element("text", {
            "class": selling_price_fraction_class,
            "transform": f"translate({decimal_x} {selling_price_y_position})",
        })
        tspan_decimal = ET.SubElement(decimal_element, "tspan", {"x": "0", "y": "0"})
        tspan_decimal.text = selling_price_fraction_part
        root.append(decimal_element) 
       
    else:
        currency_element = ET.Element("text", {
            "id": "CurrencySymbol",
            "class": currency_class,
            "transform": f"translate({currency_x_position} {currency_y_position} )",
        })
        tspan_currency = ET.SubElement(currency_element, "tspan", {"x": "0", "y": "0"})
        tspan_currency.text = f"{currency_symbol} {selling_price }{selling_price_fraction_part} "
        root.append(currency_element)
    tree.write(svg_file, xml_declaration=True, encoding="utf-8")
    print(f"SVG updated and saved to {svg_file}")

def parse_range_or_size(value):
  
    if '-' in value and value.replace('-', '').isdigit():
        return int(value.split('-')[0])
   
    size_order = ["S", "M", "L", "XL", "XXL","XXXL","3XL"]
    if value in size_order:
        return size_order.index(value)
  
    if value.isdigit():
        return int(value)
    return float('inf')

def sort_dynamic_list(data):
    return sorted(data, key=parse_range_or_size)
# genProcess('customer_order_approval','B0568777')