import os
# import labelAutomation
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

# @app.route("/labelAutomationProcess")
# def automationProcess():
#     labelAutomation.genProcess('send_for_customer_approval')
#     return 'done'

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
    # Create a cursor and execute a query to fetch all labels
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM orders")
    labels = cursor.fetchall()  # Fetch all records from the query
    cursor.close()
    
    # Pass the fetched labels to the template
    return render_template("order-list.html", labels=labels)

@app.route("/TagUpload")
def TagUpload():
    return render_template("tag-upload.html")

@app.route("/Taglist")
def Taglist():
    # Get the current page number from the query string (defaults to 1)
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of items per page
    
    # Create a cursor and execute a query to fetch total count of labels
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM label_list")
    total_labels = cursor.fetchone()['total']
    
    # Calculate total pages
    total_pages = ceil(total_labels / per_page)
    
    # Query for the labels on the current page
    offset = (page - 1) * per_page
    cursor.execute("SELECT * FROM label_list LIMIT %s OFFSET %s", (per_page, offset))
    labels = cursor.fetchall()
    cursor.close()
    
    return render_template("tag-list.html", labels=labels, total_pages=total_pages, current_page=page)

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

@app.route("/saveSvg", methods=['POST'])
def saveSvg():
    if request.method == 'POST':
        # Define the directory to save SVG files
        svgDir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'svg'))
        dynamic = 0         
       
        # Handle the uploaded SVG files
        if request.files['svgFile']:
            svgFile = request.files['svgFile']
            labelName = os.path.splitext(svgFile.filename)[0].upper()
            saveLabelName = labelName
            if "_FRONT" not in labelName:
                saveLabelName += "_FRONT"            
            saveLabelName =  saveLabelName + ".svg"
            
            svgFile.save(os.path.join(svgDir, saveLabelName))
        
        # Check if dynamic label checkbox is checked
        if request.files['svgFile_backside']:
            dynamic = 1
            svgFile_backside = request.files['svgFile_backside']
            back_side_labelName = os.path.splitext(svgFile_backside.filename)[0].upper()
            saveLabelName = back_side_labelName
            if "_BACK" not in back_side_labelName:
                saveLabelName += "_BACK"
            
            saveLabelName =  saveLabelName + ".svg"
            svgFile_backside.save(os.path.join(svgDir, saveLabelName))

        labelName = saveLabelName.replace("_FRONT", "").replace("_BACK", "")
        # Save label details in the database
        cursor = mysql.connection.cursor()        
        cursor.execute("SELECT * FROM label_list WHERE label_name = %s", (labelName,))
        data = cursor.fetchone()

        if data is None:
            cursor.execute("INSERT INTO label_list (label_name, dynamic) VALUES (%s, %s)", (labelName, dynamic))
        else:
            cursor.execute("UPDATE label_list SET label_name=%s, dynamic=%s WHERE id=%s", (labelName, dynamic, data['id']))

        mysql.connection.commit()       
        cursor.close()
        
        flash("The label has been saved successfully!")
        return redirect("/TagUpload")  

# @app.route("/saveSvg", methods=['POST'])
# def saveSvg():
#     if request.method == 'POST':
#         # Define the directory to save SVG files
#         svgDir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'static', 'svg'))
#         dynamic = 0
        
#         if 'dynamic_label' in request.form:
#             dynamic = 1
        
#         label_frontside = request.files['label_frontside']
#         frontside_lable_name = os.path.splitext(label_frontside.filename)[0].upper()
        
#         if "_FRONT" not in frontside_lable_name and "_front" not in frontside_lable_name:
#             frontside_lable_name += "_FRONT"
            
#         frontside_lable_name +=".svg"
        
#         label_frontside.save(os.path.join(svgDir, frontside_lable_name))
        
#         cursor = mysql.connection.cursor()        
#         cursor.execute("SELECT * FROM label_list WHERE label_name = %s", (frontside_lable_name,))
#         data = cursor.fetchone()

#         if data is None:
#             cursor.execute("INSERT INTO label_list (label_name, dynamic) VALUES (%s, %s)", (frontside_lable_name, dynamic))
#         else:
#             cursor.execute("UPDATE label_list SET label_name=%s, dynamic=%s WHERE id=%s", (frontside_lable_name, dynamic, data['id']))
                
#         mysql.connection.commit()       
#         cursor.close()
        
#         # Check if dynamic label checkbox is checked
#         if 'dynamic_label' in request.form:
#             label_backside = request.files['label_backside']
#             back_side_label_name = os.path.splitext(label_backside.filename)[0].upper()
        
#             if "_BACK" not in back_side_label_name and "_back" not in back_side_label_name:
#                 back_side_label_name += "_BACK"
                
#             back_side_label_name +=".svg"
            
#             label_backside.save(os.path.join(svgDir, back_side_label_name))
            
#             cursor = mysql.connection.cursor()        
#             cursor.execute("SELECT * FROM label_list WHERE label_name = %s", (back_side_label_name,))
#             data = cursor.fetchone()

#             if data is None:
#                 cursor.execute("INSERT INTO label_list (label_name, dynamic) VALUES (%s, %s)", (back_side_label_name, dynamic))
#             else:
#                 cursor.execute("UPDATE label_list SET label_name=%s, dynamic=%s WHERE id=%s", (back_side_label_name, dynamic, data['id']))
                
#             mysql.connection.commit()       
#             cursor.close()
            
        
#         flash("The label has been saved successfully!")
#         return redirect("/TagUpload")  

@app.route('/logout', methods=['GET'])
def logout():
    session.clear()
    return redirect("/login")

@app.route("/test")
def test():
    return "The app is working!"


if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0', port=9000)
