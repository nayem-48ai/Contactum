import re
from flask import Flask, request, send_file, jsonify, render_template
import io

app = Flask(__name__)

def format_number(num_str):
    bengali_digits = "০১২৩৪৫৬৭৮৯"
    english_digits = "0123456789"
    for b, e in zip(bengali_digits, english_digits):
        num_str = num_str.replace(b, e)
    clean_num = re.sub(r'\D', '', num_str)
    if clean_num.startswith('880'): clean_num = clean_num[2:]
    if clean_num.startswith('0'): return f"+88{clean_num}"
    return f"+880{clean_num}"

# ১. নাম-নম্বর থেকে VCF তৈরি
def text_to_vcf(text):
    lines = text.strip().split('\n')
    vcf_output = ""
    for line in lines:
        clean_line = re.sub(r'[•°:>]', ' ', line).strip()
        phones = re.findall(r'(?:\+?88)?01[3-9]\d{8}', clean_line)
        if phones:
            phone = phones[0]
            name = clean_line.replace(phone, '').strip() or "No Name"
            vcf_output += f"BEGIN:VCARD\nVERSION:2.1\nN:{name};;;\nTEL;CELL;PREF:{format_number(phone)}\nEND:VCARD\n"
    return vcf_output

# ২. VCF থেকে নাম-নম্বর বের করা (Reverse)
def vcf_to_text(vcf_content):
    names = re.findall(r'N:(.*?);;;', vcf_content)
    phones = re.findall(r'TEL;.*?[:](.*?)\n', vcf_content)
    result = []
    for n, p in zip(names, phones):
        result.append(f"Name: {n.strip()} | Phone: {p.strip()}")
    return "\n".join(result)

@app.route('/')
def home():
    return "VCF Converter API is Running!"

@app.route('/convert', methods=['POST'])
def convert():
    data = request.json.get('text', '')
    vcf_data = text_to_vcf(data)
    # ফাইল হিসেবে ডাউনলোড করার জন্য
    proxy_file = io.BytesIO()
    proxy_file.write(vcf_data.encode('utf-8'))
    proxy_file.seek(0)
    return send_file(proxy_file, attachment_filename="contact.vcf", as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
