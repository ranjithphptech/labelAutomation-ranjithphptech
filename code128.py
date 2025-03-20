import re
import os
import html

class BarcodeGenerator:
    def __init__(self):
        self.barcode_array = None
        
    def getBarcodeSVG(self,code, type, options = []):
        defaults = {
        'barcodeWidth' :65, 
        'barcodeHeight' :24.1, 
        'color' :'black',
        'backgroundColor' :'white', 
        'x' :0,
        'y' :0, 
        'showCode' :True, 
        'inline' :False, 
        'barWidthRatio' :1.0,
        'quietZone' :10,
        }
        
        options = {**defaults, **options}
        
        if not code or not type:
            raise ValueError("Missing required parameters: code and type")
        
        self._setBarcode(code, type)
        
        escapedCode = html.escape(code, quote=True)

        svgParts = []
        #Write headers with proper indentation
        svgParts.append('<?xml version="1.0" encoding="UTF-8"?>')
        svgParts.append('<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">')
        
        #Calculate the total original width of all bars combined
        totalOriginalWidth = 0
        for v in self.barcode_array['bcode']:
            totalOriginalWidth += v['w']
        
        #Calculate the scaling factor to fit within the desired barcodeWidth, accounting for quiet zones
        totalWidthWithQuietZone = options['barcodeWidth'] - 2 * options['quietZone']
        scale = totalWidthWithQuietZone / totalOriginalWidth
        svgHeight = round(options['barcodeHeight'], 3); # Keep the specified SVG height
        
        #Build the SVG tag with attributes and viewBox
        svgParts.append('<svg width="'+str(options['barcodeWidth']) + '" height="' +str(svgHeight) +'" version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' +str(options['barcodeWidth']) + ' ' +str(svgHeight) + '" style="background-color:' +options['backgroundColor'] + '">')
        
        
        #Start the bars group tag with color and stroke attributes
        svgParts.append( "\t" +'<g id="bars" fill="' +options['color'] +'" stroke="none">')
        
         #Initialize current X position with quiet zone
        currentX = options['x'] + options['quietZone']
        
        #Iterate through barcode data and build bars
        for v in self.barcode_array['bcode'] :
            # Calculate the scaled width and height for each bar
            bw = round((v['w'] * scale * options['barWidthRatio']), 3);
            bh = max(0.1, round((v['h'] * svgHeight / self.barcode_array['maxh']), 3)) # Ensure positive and significant bar height

            barX = currentX
            barY = options['y']# Use the 'y' value provided in the options

            if (v['t']) :
                svgParts.append("\t\t" + '<rect x="' + str(barX) + '" y="' + str(barY) + '" width="' + str(bw) + '" height="' + str(bh) + '" fill="' + options['color'] + '" />')
            
            currentX += bw
        
        
       
        #Add barcode text if enabled
        if options['showCode']:
            textX = options['barcodeWidth'] / 2
            textY = svgHeight + 4 # Adjust text Y position slightly below the barcode
            svgParts.append("\t" + '<text x="' + textX + '" y="' + textY + '" fill="' + options['color'] + '" font-size="12px" text-anchor="middle">' + escapedCode + '</text>')        
            
        #Close tags and return the SVG string
        svgParts.append("\t"+ '</g>')
        svgParts.append('</svg>')
        # print("\n".join(svgParts))
        #Return the complete SVG as a single string
        return "\n".join(svgParts)
        
    def _setBarcode(self,code, type):
            type = type.upper()  # Convert to uppercase, equivalent to strtoupper($type)
            match type:
                case 'C39':
                    arrcode = self.barcode_code39(code, False, False)
                case 'C39+':
                    arrcode = self.barcode_code39(code, False, True)
                case 'C39E':
                    arrcode = self.barcode_code39(code, True, False)
                case 'C39E+':
                    arrcode = self.barcode_code39(code, True, True)
                case 'C93':
                    arrcode = self.barcode_code93(code)
                case 'S25':
                    arrcode = self.barcode_s25(code, False)
                case 'S25+':
                    arrcode = self.barcode_s25(code, True)
                case 'I25':
                    arrcode = self.barcode_i25(code, False)
                case 'I25+':
                    arrcode = self.barcode_i25(code, True)
                case 'C128':
                    arrcode = self._barcode_c128(code, '')
                case 'C128A':
                    arrcode = self._barcode_c128(code, 'A')
                case 'C128B':
                    arrcode = self._barcode_c128(code, 'B')
                case 'C128C':
                    arrcode = self._barcode_c128(code, 'C')
                case 'EAN2':
                    arrcode = self.barcode_eanext(code, 2)
                case 'EAN5':
                    arrcode = self.barcode_eanext(code, 5)
                case 'EAN8':
                    arrcode = self.barcode_eanupc(code, 8)
                case 'EAN13':
                    arrcode = self.barcode_eanupc(code, 13)
                case 'UPCA':
                    arrcode = self.barcode_eanupc(code, 12)
                case 'UPCE':
                    arrcode = self.barcode_eanupc(code, 6)
                case 'MSI':
                    arrcode = self.barcode_msi(code, False)
                case 'MSI+':
                    arrcode = self.barcode_msi(code, True)
                case 'POSTNET':
                    arrcode = self.barcode_postnet(code, False)
                case 'PLANET':
                    arrcode = self.barcode_postnet(code, True)
                case 'RMS4CC':
                    arrcode = self.barcode_rms4cc(code, False)
                case 'KIX':
                    arrcode = self.barcode_rms4cc(code, True)
                case 'IMB':
                    arrcode = self.barcode_imb(code)
                case 'CODABAR':
                    arrcode = self.barcode_codabar(code)
                case 'CODE11':
                    arrcode = self.barcode_code11(code)
                case 'PHARMA':
                    arrcode = self.barcode_pharmacode(code)
                case 'PHARMA2T':
                    arrcode = self.barcode_pharmacode2t(code)
                case _:  # Default case
                    self.barcode_array = False
                    arrcode = False
          
            self.barcode_array = arrcode
            return arrcode
            
                
    def _barcode_c128(self,code, type = ''):
        chra = [
            "212222",  # 00
            "222122",  # 01
            "222221",  # 02
            "121223",  # 03
            "121322",  # 04
            "131222",  # 05
            "122213",  # 06
            "122312",  # 07
            "132212",  # 08
            "221213",  # 09
            "221312",  # 10
            "231212",  # 11
            "112232",  # 12
            "122132",  # 13
            "122231",  # 14
            "113222",  # 15
            "123122",  # 16
            "123221",  # 17
            "223211",  # 18
            "221132",  # 19
            "221231",  # 20
            "213212",  # 21
            "223112",  # 22
            "312131",  # 23
            "311222",  # 24
            "321122",  # 25
            "321221",  # 26
            "312212",  # 27
            "322112",  # 28
            "322211",  # 29
            "212123",  # 30
            "212321",  # 31
            "232121",  # 32
            "111323",  # 33
            "131123",  # 34
            "131321",  # 35
            "112313",  # 36
            "132113",  # 37
            "132311",  # 38
            "211313",  # 39
            "231113",  # 40
            "231311",  # 41
            "112133",  # 42
            "112331",  # 43
            "132131",  # 44
            "113123",  # 45
            "113321",  # 46
            "133121",  # 47
            "313121",  # 48
            "211331",  # 49
            "231131",  # 50
            "213113",  # 51
            "213311",  # 52
            "213131",  # 53
            "311123",  # 54
            "311321",  # 55
            "331121",  # 56
            "312113",  # 57
            "312311",  # 58
            "332111",  # 59
            "314111",  # 60
            "221411",  # 61
            "431111",  # 62
            "111224",  # 63
            "111422",  # 64
            "121124",  # 65
            "121421",  # 66
            "141122",  # 67
            "141221",  # 68
            "112214",  # 69
            "112412",  # 70
            "122114",  # 71
            "122411",  # 72
            "142112",  # 73
            "142211",  # 74
            "241211",  # 75
            "221114",  # 76
            "413111",  # 77
            "241112",  # 78
            "134111",  # 79
            "111242",  # 80
            "121142",  # 81
            "121241",  # 82
            "114212",  # 83
            "124112",  # 84
            "124211",  # 85
            "411212",  # 86
            "421112",  # 87
            "421211",  # 88
            "212141",  # 89
            "214121",  # 90
            "412121",  # 91
            "111143",  # 92
            "111341",  # 93
            "131141",  # 94
            "114113",  # 95
            "114311",  # 96
            "411113",  # 97
            "411311",  # 98
            "113141",  # 99
            "114131",  # 100
            "311141",  # 101
            "411131",  # 102
            "211412",  # 103 START A
            "211214",  # 104 START B
            "211232",  # 105 START C
            "233111",  # STOP
            "200000"   # END
        ]
        keys_a = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_'
        keys_a += "".join(chra)  # ASCII 0-31
        
        #ASCII characters for code B (ASCII 32 - 127)
        keys_b = ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'+"".join(chr(127))
        # special codes
        fnc_a = {241: 102, 242: 97, 243: 96, 244: 101}
        fnc_b = {241: 102, 242: 97, 243: 96, 244: 100}
        #array of symbols
        code_data = []
        #lenght of the code
        len_code = len(code)
        match type.upper():
            case 'A':
                startid = 103
                for i in range(len_code):
                    char = code[i]
                    char_id = ord(char)
                    if 241 <= char_id <= 244:
                        code_data.append(fnc_a[char_id])
                    elif 0 <= char_id <= 95:
                        try:
                            code_data.append(keys_a.index(char))
                        except ValueError:
                            return False
                    else:
                        return False
            case 'B':
                startid = 104
                for i in range(len_code):
                    char = code[i]
                    char_id = ord(char)

                    if 241 <= char_id <= 244:
                        code_data.append(fnc_b[char_id])
                    elif 32 <= char_id <= 127:
                        try:
                            code_data.append(keys_b.index(char))
                        except ValueError:
                            return False 
                    else:
                        return False 
            case 'C':
                startid = 105
                if ord(code[0]) == 241:
                    code_data.append(102)
                    code = code[1:]
                    len_code -= 1

                if len_code % 2 != 0:
                    return False

                for i in range(0, len_code, 2):
                    chrnum = code[i:i+2]
                    if chrnum.isdigit():
                        code_data.append(int(chrnum))
                    else:
                        return False
            case _:
                #MODE AUTO
                # split code into sequences
                sequence = []
                #get numeric sequences (if any)
                numseq = []
                numseq = re.findall(r"([0-9]{4,})", code)
                numseq_with_offsets = [(match.group(), match.start()) for match in re.finditer(r"([0-9]{4,})", code)]

                if numseq_with_offsets:
                    end_offset = 0
                    for match, offset in numseq_with_offsets:
                        if offset > end_offset:
                            sequence.extend(self.get128ABsequence(code[end_offset:offset]))
                        slen = len(match)
                        if slen % 2 != 0:
                            slen -= 1
                        sequence.append(('C', code[offset:offset+slen], slen))
                        end_offset = offset + slen
                    if end_offset < len(code):
                        sequence.extend(self.get128ABsequence(code[end_offset:]))
                else:
                    sequence.extend(self.get128ABsequence(code))
                
                for key, seq in enumerate(sequence):  # Use enumerate for index and value
                    match seq[0]:  
                        case 'A':
                            if key == 0:
                                startid = 103
                            elif sequence[key - 1][0] != 'A':
                                if seq[2] == 1 and key > 0 and sequence[key - 1][0] == 'B' and len(sequence[key - 1]) < 4:  # Check for element existence
                                    code_data.append(98)
                                    seq = list(seq) #seq is a tuple and is immutable. Convert to list to modify
                                    seq.append(True)  # Mark shift
                                    sequence[key] = tuple(seq) #Convert back to tuple and update sequence
                                elif len(sequence[key - 1]) < 4:  # Check for element existence
                                    code_data.append(101)
                            for i in range(seq[2]):
                                char = seq[1][i]
                                char_id = ord(char)
                                if 241 <= char_id <= 244:
                                    code_data.append(fnc_a[char_id])
                                else:
                                    code_data.append(keys_a.index(char))
                        case 'B':
                            if key == 0:
                                tmpchr = ord(seq[1][0])
                                if seq[2] == 1 and 241 <= tmpchr <= 244 and key + 1 < len(sequence) and sequence[key + 1][0] != 'B': #Check for element existence
                                    match sequence[key + 1][0]:
                                        case 'A':
                                            startid = 103
                                            seq = list(seq) #seq is a tuple and is immutable. Convert to list to modify
                                            seq[0] = 'A'
                                            sequence[key] = tuple(seq) #Convert back to tuple and update sequence
                                            code_data.append(fnc_a[tmpchr])
                                        case 'C':
                                            startid = 105
                                            seq = list(seq) #seq is a tuple and is immutable. Convert to list to modify
                                            seq[0] = 'C'
                                            sequence[key] = tuple(seq) #Convert back to tuple and update sequence
                                            code_data.append(fnc_a[tmpchr])
                                else:
                                    startid = 104
                            elif sequence[key - 1][0] != 'B':
                                if seq[2] == 1 and key > 0 and sequence[key - 1][0] == 'A' and len(sequence[key - 1]) < 4: # Check for element existence
                                    code_data.append(98)
                                    seq = list(seq) #seq is a tuple and is immutable. Convert to list to modify
                                    seq.append(True)  # Mark shift
                                    sequence[key] = tuple(seq) #Convert back to tuple and update sequence
                                elif len(sequence[key - 1]) < 4:  # Check for element existence
                                    code_data.append(100)
                            for i in range(seq[2]):
                                char = seq[1][i]
                                char_id = ord(char)
                                if 241 <= char_id <= 244:
                                    code_data.append(fnc_b[char_id])
                                else:
                                    code_data.append(keys_b.index(char))
                        case 'C':
                            if key == 0:
                                startid = 105
                            elif sequence[key - 1][0] != 'C':
                                code_data.append(99)
                            for i in range(0, seq[2], 2):
                                chrnum = seq[1][i:i+2] #String slice for two characters
                                code_data.append(int(chrnum))
        #calculate check character
        sum = startid
        
        for key,val in enumerate(code_data):
            sum += (val * (key + 1))
        #add check character
        code_data.append(sum % 103)
        #add stop sequence
        code_data.append(106)
        code_data.append(107)
        #add start code at the beginning
        code_data.insert(0, startid)
        bararray = {'code':code, 'maxw':0, 'maxh' :1, 'bcode' :[]}
        for val in code_data:
            seq = chra[int(val)]
            for j in range(6):
                t = True if j % 2 == 0 else False 
                w = int(seq[j])
                bararray['bcode'].append({'t' : t, 'w' : w, 'h' : 1, 'p' : 0})
                bararray['maxw'] += w
        
        return bararray
    

generator = BarcodeGenerator()
barcodeno = '8054717431360016'       
x = float(195.37)      

y = float(69.52)
width = float(79)  
width = width+1
default_array = {
    "barcodeWidth": 65,
    "barcodeHeight": 24.1,
    "color": 'cmyk(0,0,0,100)',
    "x": 0,
    "y": 0,
    "showCode": False,
    "inline": True,
    "barWidthRatio": 1.0,
    "quietZone": 10
}
svg_output = generator.getBarcodeSVG(barcodeno, "C128C", default_array)  

directory = "barcode_svg"
filename = f"{barcodeno}.svg"
file_path = os.path.join(directory, filename)
os.makedirs(directory, exist_ok=True)    

with open(file_path, "w", encoding="utf-8") as file:
    file.write(svg_output)