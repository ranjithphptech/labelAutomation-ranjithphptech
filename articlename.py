import xml.etree.ElementTree as ET
import re
def wrap_text_to_fit(text, max_width, font_size, avg_char_width=0.6):
    words = text.split()
    lines = []
    current_line = ""   
    max_chars_per_line = int(max_width / (font_size * avg_char_width))

    for word in words:
        if len(current_line) + len(word) <= max_chars_per_line:
            current_line += " " + word if current_line else word
        else:
            lines.append(current_line)
            current_line = word

    lines.append(current_line)  
    return lines

def extract_text_attributes(root, text_id):
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)
    text_element = root.find(f".//*[@id='{text_id}']")
    if text_element is None:
        print(f"Error: Text element with id '{text_id}' not found.")
        return None, None, None, None

    x_pos = text_element.get('x', '50') 
    y_pos = text_element.get('y', '50')  
    style = text_element.get('style', "fill: black; font-size: 5px;")  
    font_size_match = re.search(r'font-size:\s*([\d.]+)px', style)
    font_size = float(font_size_match.group(1)) if font_size_match else 5 
    return float(x_pos.replace('%', '')), float(y_pos.replace('%', '')), font_size, style

def add_wrapped_text_to_svg(root, text, text_id, max_width, line_spacing):
    x_pos, y_pos, font_size, text_style = extract_text_attributes(root, text_id)
    if x_pos is None or y_pos is None or text_style is None:
        return  
   
    SVG_NS = "http://www.w3.org/2000/svg"
    ET.register_namespace("", SVG_NS)
    wrapped_lines = wrap_text_to_fit(text, max_width, font_size)
    text_element = ET.Element('text', {
        'id': text_id,
        'text-anchor': 'end',
        'style': text_style
    })


    for i, line in enumerate(wrapped_lines):
        tspan_element = ET.SubElement(text_element, 'tspan', {
            'x': f'{x_pos}%',
            'y': f'{y_pos + (i * line_spacing)}%'  
        })
        tspan_element.text = line

  
    root.append(text_element)
    