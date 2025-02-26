import ean13barcode as bc
import xml.etree.ElementTree as ET
import os


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

generator = bc.BarcodeGenerator()
barcodeno="8054031547661"
x=37
x=x-10.5
y=65
width=67
width =width+38

default_array={
    "barcodeWidth": width,
    "barcodeHeight": 30.5,
    "color":'cmyk(0,0,0,100)',
    "x": x,
    "y": y,
    "showCode": False,
    "inline": True,
    "barWidthRatio":0.8,
    "quietZone": 20
}

svg_output = generator.get_barcode_svg(barcodeno, "EAN13", default_array)
directory = "barcode_svg"
filename = f"{barcodeno}.svg"
file_path = os.path.join(directory, filename)
os.makedirs(directory, exist_ok=True)
with open(file_path, "w", encoding="utf-8") as file:
    file.write(svg_output)

print(f"Barcode saved at: {file_path}")
rects_string = get_rects_as_string(file_path)
print("Extracted <rect> content as string:")
print(rects_string)



