import os
import shutil

from zipfile import ZipFile
import xml.etree.ElementTree as ET

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

from db import conn
from helpers import *


current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)


PAGE_WIDTH,PAGE_HEIGHT = letter
totRowImageWidth = 0.0
nxt_x_position=5.0
nxt_y_position=0.0
imageRowNo = 1


def center_image_horizontally(c, drawing, width,height):
    global totRowImageWidth
    global nxt_x_position
    global nxt_y_position
    page_width, _ = letter
    drawing_width = width
    drawing_height = height
    totRowImageWidth += drawing_width+5
    # print(totRowImageWidth,' - ',page_width)
    # print(totRowImageWidth>page_width)
    # print('img height : '+str(drawing_height))
    if totRowImageWidth>page_width:
        # print('lnxt y '+str(nxt_y_position))
        # print('dh  '+str(drawing_height))
        nxt_y_position -= drawing_height+5
        # print('nxt y '+str(nxt_y_position))
        totRowImageWidth = 0.0
        nxt_x_position = 5.0
        renderPDF.draw(drawing, c,nxt_x_position, nxt_y_position)
        nxt_x_position = nxt_x_position + drawing_width+5
    else:       
        # print(nxt_x_position)
        # print(nxt_y_position)
        renderPDF.draw(drawing, c,nxt_x_position, nxt_y_position)   
        nxt_x_position = nxt_x_position + drawing_width+5
       
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
        global totRowImageWidth
        global nxt_x_position
        global nxt_y_position
        print("process is going on "+zipFile)

        f = os.path.join(orderProcessing,zipFile)
        ordersData = {}
        with ZipFile(f,'r') as zObject:
             designCodes =[]
             currentZipOutputDir = orderOutputDir+"/"+baseNameofZip
             Path(currentZipOutputDir).mkdir(parents=True, exist_ok=True)
             zObject.extractall(currentZipOutputDir)
             for xmlFile in Path(currentZipOutputDir).rglob('*.xml'):
                  #Reset x,y position
                totRowImageWidth = 0.0
                nxt_x_position=5.0
                XMLDir = os.path.splitext(xmlFile)[0]
                xmlFilename =  os.path.basename(xmlFile).split('/')[-1]
                xmlFileBasename = os.path.splitext(xmlFilename)[0]
                designCodes.append(xmlFileBasename)
                csep = ","
                Path(XMLDir).mkdir(parents=True, exist_ok=True)
                XMLtree = ET.parse(xmlFile)
                XMLRoot = XMLtree.getroot()                    
                orderID = XMLtree.find('OrderID').text
                customerID = XMLtree.find('CustomerID').text
                customerName = XMLtree.find('CustomerName').text
                customerEmail = XMLtree.find('CustomerEmail').text
                createdDate = XMLtree.find('CreatedDate').text
                ordersData[orderID] = {
                'customerID':customerID,
                'customerName':customerName,
                'customerEmail':customerEmail,
                'createdDate':createdDate,
                }
                assetName = XMLRoot.find("./OrderItems/OrderItem/Asset/Name").text
                assetName = assetName.strip()      
                svgString=svgDir+'/'+assetName+'.svg'
                namespaces = {node[0]: node[1] for _, node in ET.iterparse(svgString, events=['start-ns'])}
                for key, value in namespaces.items():
                    ET.register_namespace(key, value)
                SVGtree = ET.parse(svgString)
                SVGroot = SVGtree.getroot()
                vby = float(SVGroot.attrib['viewBox'].split()[3])
                if vby<=131.51:
                    nxt_y_position = 450
                else:
                    vbyn = vby - 131.51
                    nxt_y_position = 475 - vbyn 
                    
                for item in XMLRoot.findall("./OrderItems/OrderItem/Item"):
                    itemID = item.find('./ItemID').text
                    qty = item.find('./Quantity').text                    
                    SVGroot.find(".//*[@id='Quantity']")[0].text = qty
                    sizeChartItem = item.findall("./SizeChartItem")
                    for size in item.findall("./SizeChartItem/Size"):
                        nameAttr = size.attrib['Name'].replace(' ','_')
                        if SVGroot.find(".//*[@id='"+nameAttr+"']") is not None:
                            SVGroot.find(".//*[@id='"+nameAttr+"']")[0].text = size.attrib['Value']
                            
                    SVGtree.write(currentZipOutputDir+'/'+xmlFileBasename+'/'+itemID+'.svg')
                    
                isPDFOutputDir = os.path.exists(currentZipOutputDir+'/pdf')
                Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)
                if isPDFOutputDir==False:
                    Path(currentZipOutputDir+'/pdf').mkdir(parents=True, exist_ok=True)  
                c=canvas.Canvas(currentZipOutputDir+'/pdf/'+assetName+'.pdf',pagesize=letter)
                title = assetName+" - "+orderID
                text_width = c.stringWidth(title, "Helvetica", 14)                
                x_pos_for_title = (PAGE_WIDTH - text_width) / 2
                c.setFillColor(colors.red)
                c.drawString(x_pos_for_title, 670, title)
                buyerTxt         = 'BUYER               : OVS'
                customerNameTxt  = 'CUSTOMER        : '+customerName
                designCodeTxt    = 'DESIGN CODE     : '+assetName
                submittedDateTxt = 'SUBMITTED DATE  : '+createdDate
                data=  [[Image(current_dir+"/Sainmarknewlogo.png",width=100, height=40,hAlign='center'), '', buyerTxt, '03', 'ARTWORK\nFOR\nAPPROVAL','05'],
                    ['', '', customerNameTxt, '13', '14','15'],
                    ['20', '21', designCodeTxt, '23', '24','25'],
                    ['30', '31', submittedDateTxt, '33', '34','35'],
                    ['', '', '', '', '','']]

                x = 40
                y = 700    
                table = Table(data, colWidths=[40,70,250,70,40], rowHeights=14)
                style = TableStyle([
                ('GRID',(0,0),(-1,-1),0.5,colors.black),
                ('SPAN',(0,0),(1,4)),
                ('SPAN',(-2,-5),(-1,-1)),
                ('SPAN',(2,0),(3,0)),
                ('SPAN',(2,1),(3,1)),
                ('SPAN',(2,2),(3,2)),
                ('SPAN',(2,3),(3,3)),
                ('SPAN',(2,4),(3,4)),
                ('ALIGN', (4,0), (-1,-1), 'CENTER'),
                ('VALIGN', (0,0),(-1,-1), 'MIDDLE')
                ])
                table.setStyle(style)
                table.wrapOn(c, 600, 200)
                table.drawOn(c, x, y)
                c.translate(cm,cm)
                for svgFile in Path(currentZipOutputDir+'/'+xmlFileBasename).rglob('*.svg'):
                    drawing = svg2rlg(svgFile)
                    img_width = drawing.width
                    img_height = drawing.height    
                    center_image_horizontally(c, drawing,img_width,img_height)
                c.showPage()
                c.save()
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
        res = send_mail(subject='Subject',toMailid='ranjith@indsys.holdings',attachmentPath=currentZipOutputDir+'/pdf')
        
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
        print('An exception occurred: {}'.format(error))
        shutil.move(orderProcessing+'/'+baseNameofZip+'.zip', failedOrders+'/'+baseNameofZip+'.zip')
        dbcursor = conn.cursor()
        dbcursor.execute("INSERT INTO failed_orders(order_id,error,status,created_date_time) VALUES('"+currentOrderId+"','"+str(format(error)).replace("'",'"').strip()+"','F','"+str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))+"')")
        conn.commit()
