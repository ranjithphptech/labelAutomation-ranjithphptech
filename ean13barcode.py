import math
from xml.sax.saxutils import escape


class BarcodeGenerator:
    def __init__(self):
        self.barcode_array = None

    def set_barcode(self, code, barcode_type):
        barcode_type = barcode_type.upper()
        if barcode_type == "EAN8":
            self.barcode_array = self.barcode_eanupc(code, 8)
        elif barcode_type == "EAN13":
            self.barcode_array = self.barcode_eanupc(code, 13)
        else:
            self.barcode_array = None
            raise ValueError("Unsupported barcode type")

    def upce_to_upca(upce_code):
        if len(upce_code) != 6 or not upce_code.isdigit():
            raise ValueError("UPC-E code must be a 6-digit number.")       
        manufacturer = upce_code[:3]
        product_code = upce_code[3:6]
        last_digit = upce_code[5]

        if last_digit == "0" or last_digit == "1" or last_digit == "2":
          
            upca = f"{manufacturer}{last_digit}00000{product_code[0]}"
        elif last_digit == "3":
            # If last digit is 3, it goes into the middle with "0000"
            upca = f"{manufacturer}{product_code[0]}00000{product_code[1]}"
        elif last_digit == "4":
            upca = f"{manufacturer}{product_code[:2]}00000{product_code[2]}"
        else:
            upca = f"{manufacturer}{product_code}0000{last_digit}"  
                
        check_digit = __class__.calculate_check_digit(upca)
        return f"{upca}{check_digit}"

    def calculate_check_digit(upca_code):   
        if len(upca_code) != 11 or not upca_code.isdigit():
            raise ValueError("UPC-A code must be 11 digits to calculate the check digit.")

        sum_odd = sum(int(upca_code[i]) for i in range(0, 11, 2))
        sum_even = sum(int(upca_code[i]) for i in range(1, 11, 2))
        total = (sum_odd * 3) + sum_even
        return (10 - (total % 10)) % 10
    
    def barcode_eanupc(self, code, length=13):
        if not code.isdigit():
            raise ValueError(f"Code must be digits only. Got: {code}")

        upce = False
        if length == 6:
            length = 12  
            upce = True

        data_length = length - 1
        
        if upce:
            code = self.upce_to_upca(code)
        else:
            code = code.zfill(data_length)

        code_length = len(code)
        
        sum_a = sum(int(code[i]) for i in range(1, data_length, 2))
        if length > 12:
            sum_a *= 3

        sum_b = sum(int(code[i]) for i in range(0, data_length, 2))
        if length < 13:
            sum_b *= 3

        check_digit = (10 - (sum_a + sum_b) % 10) % 10
        
        if code_length == data_length:
            code += str(check_digit)
        elif int(code[data_length]) != check_digit:
            raise ValueError(f"Wrong check digit: expected {check_digit}, got {code[data_length]}")

        if length == 12:
            code = '0' + code
            length += 1
        
        if upce:
            tmp = code[4:7]
            if tmp in ['000', '100', '200']:
                upce_code = code[2:4] + code[9:12] + code[4:5]
            else:
                tmp = code[5:7]
                if tmp == '00':
                    upce_code = code[2:5] + code[10:12] + '3'
                else:
                    tmp = code[6]
                    if tmp == '0':
                        upce_code = code[2:6] + code[11] + '4'
                    else:
                        upce_code = code[2:7] + code[11]
        else:
            upce_code = None

        codes = {
            "A": {"0": "0001101", "1": "0011001", "2": "0010011", "3": "0111101",
                  "4": "0100011", "5": "0110001", "6": "0101111", "7": "0111011",
                  "8": "0110111", "9": "0001011"},
            "B": {"0": "0100111", "1": "0110011", "2": "0011011", "3": "0100001",
                  "4": "0011101", "5": "0111001", "6": "0000101", "7": "0010001",
                  "8": "0001001", "9": "0010111"},
            "C": {"0": "1110010", "1": "1100110", "2": "1101100", "3": "1000010",
                  "4": "1011100", "5": "1001110", "6": "1010000", "7": "1000100",
                  "8": "1001000", "9": "1110100"}
        }

        parities = {
            '0': ['A', 'A', 'A', 'A', 'A', 'A'],
            '1': ['A', 'A', 'B', 'A', 'B', 'B'],
            '2': ['A', 'A', 'B', 'B', 'A', 'B'],
            '3': ['A', 'A', 'B', 'B', 'B', 'A'],
            '4': ['A', 'B', 'A', 'A', 'B', 'B'],
            '5': ['A', 'B', 'B', 'A', 'A', 'B'],
            '6': ['A', 'B', 'B', 'B', 'A', 'A'],
            '7': ['A', 'B', 'A', 'B', 'A', 'B'],
            '8': ['A', 'B', 'A', 'B', 'B', 'A'],
            '9': ['A', 'B', 'B', 'A', 'B', 'A']
        }

        upce_parities = [
            {'0': ['B', 'B', 'B', 'A', 'A', 'A'], '1': ['B', 'B', 'A', 'B', 'A', 'A'], '2': ['B', 'B', 'A', 'A', 'B', 'A'],
             '3': ['B', 'B', 'A', 'A', 'A', 'B'], '4': ['B', 'A', 'B', 'B', 'A', 'A'], '5': ['B', 'A', 'A', 'B', 'B', 'A'],
             '6': ['B', 'A', 'A', 'A', 'B', 'B'], '7': ['B', 'A', 'B', 'A', 'B', 'A'], '8': ['B', 'A', 'B', 'A', 'A', 'B'],
             '9': ['B', 'A', 'A', 'B', 'A', 'B']},
            {'0': ['A', 'A', 'A', 'B', 'B', 'B'], '1': ['A', 'A', 'B', 'A', 'B', 'B'], '2': ['A', 'A', 'B', 'B', 'A', 'B'],
             '3': ['A', 'A', 'B', 'B', 'B', 'A'], '4': ['A', 'B', 'A', 'A', 'B', 'B'], '5': ['A', 'B', 'B', 'A', 'A', 'B'],
             '6': ['A', 'B', 'B', 'B', 'A', 'A'], '7': ['A', 'B', 'A', 'B', 'A', 'B'], '8': ['A', 'B', 'A', 'B', 'B', 'A'],
             '9': ['A', 'B', 'B', 'A', 'B', 'A']}
        ]

        seq = '101' 
        bar_array = {'code': code, 'maxw': 0, 'maxh': 1, 'bcode': []}

        if upce:
            p = upce_parities[int(code[1])][check_digit]
            for i in range(6):
                seq += codes[p[i]][code[i]]
            seq += '010101' 
        else:
            half_length = (length + 1) // 2
            parity = parities[code[0]]

            for i in range(1, half_length):
                seq += codes[parity[i - 1]][code[i]]

            seq += '01010' 
            for i in range(half_length, length):
                seq += codes['C'][code[i]]

            seq += '101'

        # Convert sequence to bars
        current_width = 0
        for i, char in enumerate(seq):
            current_width += 1
            if i == len(seq) - 1 or seq[i] != seq[i + 1]:
                bar_array['bcode'].append({'t': char == '1', 'w': current_width, 'h': 1, 'p': 0})
                bar_array['maxw'] += current_width
                current_width = 0

        return bar_array

    def get_barcode_svg_old(self, code, barcode_type, options=None):
        if options is None:
            options = {}

        defaults = {
            "barcodeWidth": 200,
            "barcodeHeight": 60,
            "color": "black",
            "backgroundColor": "transparent",
            "x": 0,
            "y": 0,
            "showCode": True,
            "inline": False,
            "barWidthRatio": 1.0,
            "quietZone": 20,
        }
        options = {**defaults, **options}

        self.set_barcode(code, barcode_type)

        if not self.barcode_array.get("bcode"):
            raise ValueError("Barcode array is empty or invalid.")
       
        total_bar_width = sum(bar["w"] * options["barWidthRatio"] for bar in self.barcode_array["bcode"])
        quiet_zone_width = 2 * options["quietZone"]
        calculated_width = total_bar_width + quiet_zone_width+ options["x"]
        svg_width = max(calculated_width, options["barcodeWidth"])

        max_bar_height = max(bar["h"] for bar in self.barcode_array["bcode"]) * options["barcodeHeight"]
        text_height = 14 if options["showCode"] else 0
        calculated_height = max_bar_height + text_height + options["y"] + 10

        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{options["barcodeWidth"]}" '
            f'height="{calculated_height}" '
            f'style="">',
        ]

        current_x = options["x"] + options["quietZone"]
        
        for bar in self.barcode_array["bcode"]:
            bar_width = bar["w"] * options["barWidthRatio"]
            bar_height = bar["h"] * options["barcodeHeight"]
            if bar["t"]:  
                svg_parts.append(
                    f'<rect x="{current_x}" y="{options["y"]}" '
                    f'width="{bar_width}" height="{bar_height}" '
                    f'fill="{options["color"]}" />'
                )
            current_x += bar_width

        if options["showCode"]:
            text_y_position = options["y"] + max_bar_height + 10
            svg_parts.append(
                f'<text x="{svg_width / 2}" '
                f'y="{text_y_position}" '
                f'fill="{options["color"]}" font-size="14" text-anchor="middle">{code}</text>'
            )

        svg_parts.append("</svg>")
        return "\n".join(svg_parts)
    
    def get_barcode_svg(self, code, barcode_type, options=None):
        if options is None:
            options = {}

        defaults = {
            "barcodeWidth": 200,  
            "barcodeHeight": 60,
            "color": "black",
            "backgroundColor": "transparent",
            "x": 0,
            "y": 0,
            "showCode": True,
            "inline": False,
            "barWidthRatio": 1.0,
            "quietZone": 20,
        }
        options = {**defaults, **options}
        self.set_barcode(code, barcode_type)
        
        if not self.barcode_array.get("bcode"):
            raise ValueError("Barcode array is empty or invalid.")        
        
        total_bar_width = sum(bar["w"] * options["barWidthRatio"] for bar in self.barcode_array["bcode"])
        quiet_zone_width = 2 * options["quietZone"]         
        calculated_width = total_bar_width + quiet_zone_width + options["x"]       
       
        svg_width = options["barcodeWidth"]
        
        if calculated_width > svg_width:
            scaling_factor = svg_width / total_bar_width if total_bar_width > 0 else 1
        else:
            scaling_factor = 1  
    
        max_bar_height = max(bar["h"] for bar in self.barcode_array["bcode"]) * options["barcodeHeight"]
        text_height = 14 if options["showCode"] else 0
        calculated_height = max_bar_height + text_height + options["y"] + 10

        svg_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{svg_width}" '  # Use the fixed svg_width
            f'height="{calculated_height}" '
            f'style="">',
        ]

        current_x = options["x"] + options["quietZone"]
        
        for bar in self.barcode_array["bcode"]:
            bar_width = bar["w"] * options["barWidthRatio"] * scaling_factor 
            bar_height = bar["h"] * options["barcodeHeight"]
            if bar["t"]:  
                svg_parts.append(
                    f'<rect x="{current_x}" y="{options["y"]}" '
                    f'width="{bar_width}" height="{bar_height}" '
                    f'fill="{options["color"]}" />'
                )
            current_x += bar_width

        if options["showCode"]:
            text_y_position = options["y"] + max_bar_height + 10
            svg_parts.append(
                f'<text x="{svg_width / 2}" '
                f'y="{text_y_position}" '
                f'fill="{options["color"]}" font-size="14" text-anchor="middle">{code}</text>'
            )

        svg_parts.append("</svg>")
        
        return "\n".join(svg_parts)


  





