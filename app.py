import os
from flask import Flask, session, render_template, request, redirect, url_for, flash,jsonify
from flask_mysqldb import MySQL
from math import ceil   
import configparser

app = Flask(__name__)
app.config.update(
    TEMPLATES_AUTO_RELOAD=True
)

config = configparser.ConfigParser()
config.read('config.ini')

app.config['MYSQL_HOST'] = config['database']['host']
app.config['MYSQL_USER'] = config['database']['user']
app.config['MYSQL_PASSWORD'] = config['database']['password']
app.config['MYSQL_DB'] = config['database']['databaseName']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
mysql = MySQL(app)  

app.secret_key = '9EjBl9tcMa16nFcsV2YH'

# Directory to store SVG files and new order files
STATIC_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'svg')
NEW_ORDERS = os.path.join(os.path.dirname(__file__), 'new_orders')

# Ensure static directories exist
os.makedirs(STATIC_FOLDER, exist_ok=True)
os.makedirs(NEW_ORDERS, exist_ok=True)

# Function to check if the uploaded file is a .zip file
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'zip'

@app.route("/")
def home():
    if session.get('id'):
        return redirect("/TagUpload")
    else:
        return redirect("/login")

@app.route("/login", methods=['POST', 'GET'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
   
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        cr = mysql.connection.cursor()
        cr.execute("SELECT * FROM users WHERE email=%s AND password=%s", (email, password))
        user = cr.fetchone()
        if user:
            session['id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            return redirect("/TagUpload")
        else:
            flash("Invalid email or password.")
            return redirect("/login")

@app.route("/OrderUpload")
def OrderUpload():
    return render_template("order-upload.html")

@app.route("/Orderlist")
def Orderlist():
    
    # Get the page number from the URL (default to 1)
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of records per page
    offset = (page - 1) * per_page
    
    # Create a cursor and execute a query to fetch total count of labels
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM orders")
    total_orders = cursor.fetchone()['total']
    
    # Calculate total pages
    total_pages = ceil(total_orders / per_page)    
    # Query for the orders on the current page
    query = "SELECT o.*,fo.status failed_status,fo.error,fo.created_date_time as failed_datetime FROM orders o LEFT JOIN failed_orders fo ON fo.order_id=o.order_id LIMIT %s OFFSET %s"
    
    cursor.execute(query, (per_page, offset))
    orders = cursor.fetchall()
    cursor.close()
    for order in orders:
        if order['approval_mail_status']=='F':
            if order['status']=='CAP':
               order['status'] = "Failed"
        elif order['approval_mail_status']=='S':
            if order['status']=='CAP':
                order['status'] = "Approval Pending"
            elif order['status']=='CAA':
                order['status'] = "Approved"
        if order['created_date_time']:
            order['created_date_time'] = order['created_date_time'].strftime("%d-%m-%Y %H:%M:%S")
            
        if order['failed_datetime']:
            order['failed_datetime'] = order['failed_datetime'].strftime("%d-%m-%Y %H:%M:%S")
    
    return render_template("order-list.html", orders=orders,total_pages=total_pages, page=page)

@app.route("/TagUpload")
def TagUpload():
    return render_template("tag-upload.html")

@app.route("/Taglist")
def Taglist():
   # Get the page number from the URL (default to 1)
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of records per page
    offset = (page - 1) * per_page
    
    # Create a cursor and execute a query to fetch total count of labels
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM label_list")
    total_labels = cursor.fetchone()['total']
    
    # Calculate total pages
    total_pages = ceil(total_labels / per_page)
    
    # Query for the labels on the current page
    cursor.execute("SELECT * FROM label_list LIMIT %s OFFSET %s", (per_page, offset))
    labels = cursor.fetchall()
    
    # Modify the result as needed
    for label in labels:
        
        frontLabel = label['label_name'].replace('.svg', '_FRONT.svg')
        frontLabelPath = os.path.join(STATIC_FOLDER, frontLabel)
        if not os.path.exists(frontLabelPath):
            frontLabel = ''

        backLabel = label['label_name'].replace('.svg', '_BACK.svg')
        backLabelPath = os.path.join(STATIC_FOLDER, backLabel)
        if not os.path.exists(backLabelPath):
            backLabel = ''
        
        label['frontLabel'] = frontLabel
        label['backLabel'] = backLabel
    
    cursor.close()
    
    return render_template("tag-list.html", labels=labels, total_pages=total_pages, page=page)

@app.route("/saveOrder", methods=['POST'])
def saveOrder():
    if request.method == 'POST':
        # Get the uploaded file
        orderFile = request.files['orderFile']
        
        # Ensure the file is not empty and has a .zip extension
        if orderFile and orderFile.filename.endswith('.zip'):
            orderFileName = orderFile.filename  # Get the filename of the uploaded file
            orderFilePath = os.path.join(NEW_ORDERS, orderFileName)  # Path to save the file
            
            # Save the file in the 'new_orders' folder
            orderFile.save(orderFilePath)

            # Flash success message and redirect back to the upload page
            flash("Order file uploaded successfully!")
            return redirect("/OrderUpload")
        else:
            flash("Only .zip files are allowed.")
            return redirect("/OrderUpload")

@app.route("/saveTag", methods=['POST'])
def saveTag():
    if request.method == 'POST':
        design_code = request.form.get('design_code', None).replace("  ", " ").upper()
        product_code = request.form.get('product_code', None).replace("  ", " ").upper()

        # Define the directory to save SVG files
        svgDir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'svg'))
        dynamic = request.form.get('dynamic_label', 0)
        
        # Handle the uploaded SVG files
        if request.files['svgFile_frontside']:
            svgFile_frontside = request.files['svgFile_frontside']            
            saveLabelName =  design_code+"_"+product_code+"_FRONT.svg"
            svgFile_frontside.save(os.path.join(svgDir, saveLabelName))
        
        # Check if dynamic label checkbox is checked
        if request.files['svgFile_backside']:
            svgFile_backside = request.files['svgFile_backside']
            back_side_labelName = os.path.splitext(svgFile_backside.filename)[0].upper()
            saveLabelName = back_side_labelName.upper()
            
            saveLabelName = design_code+"_"+product_code+"_BACK.svg"
            svgFile_backside.save(os.path.join(svgDir, saveLabelName))

        labelName = (design_code+"_"+product_code).replace("_FRONT", "").replace("_BACK", "")+".svg"
        design_code = design_code.replace("_FRONT", "").replace("_BACK", "")
        # Save label details in the database
        cursor = mysql.connection.cursor()        
        query = "SELECT * FROM label_list WHERE design_code = %s AND product_code=%s"
        params = (design_code, product_code)        
        cursor.execute(query, params)
        data = cursor.fetchone()
        
        if data is None:
            cursor.execute("INSERT INTO label_list (design_code,label_name, product_code, dynamic) VALUES (%s,%s,%s,%s)", (design_code, labelName, product_code, dynamic))
        else:
            cursor.execute("UPDATE label_list SET design_code=%s,label_name=%s,product_code=%s,dynamic=%s WHERE id=%s", (design_code, labelName, product_code, dynamic, data['id']))

        mysql.connection.commit()       
        cursor.close()
        
        flash("The label has been saved successfully!")
        return redirect("/TagUpload")  

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect("/login")

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=8000,ssl_context=('cert.pem', 'key.pem'))