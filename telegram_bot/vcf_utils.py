import re

def format_number(num_str):
    # বাংলা সংখ্যাকে ইংরেজিতে রূপান্তর
    bengali_digits = "০১২৩৪৫৬৭৯" # 8 এর বদলে ৯, কারণ বাংলা ৮ (৮) দেখতে ইংরেজি 8 এর মতো।
    english_digits = "0123456789"
    for b, e in zip(bengali_digits, english_digits):
        num_str = num_str.replace(b, e)
    
    # শুধু সংখ্যাগুলো বের করে আনা
    clean_num = re.sub(r'\D', '', num_str)
    
    # নম্বর ফরম্যাটিং
    if clean_num.startswith('880'):
        clean_num = clean_num[2:] # ৮৮ বাদ দিয়ে শুরু
    
    # নিশ্চিত করা যে নম্বরটি 01 দিয়ে শুরু এবং 11 ডিজিটের
    if clean_num.startswith('01') and len(clean_num) == 11:
        return f"+88{clean_num}"
    elif len(clean_num) == 10 and clean_num.startswith('1'): # যদি 01 ছাড়া 1 দিয়ে শুরু হয় এবং 10 ডিজিটের হয়
         return f"+880{clean_num}"
    else:
        # যদি ফরম্যাট না মেলে, তাহলে যেমন আছে তেমনই ফিরিয়ে দেওয়া (অথবা একটি এরর হ্যান্ডেল করা যেতে পারে)
        return num_str


def create_vcf(name, phone):
    formatted_phone = format_number(phone)
    # VCF 2.1 ফরম্যাট
    vcf_template = f"BEGIN:VCARD\nVERSION:2.1\nN:{name};;;\nTEL;CELL;PREF:{formatted_phone}\nEND:VCARD"
    return vcf_template

def process_bulk(text):
    # সিম্বলগুলো সরিয়ে ক্লিন করা
    lines = re.split(r'\n', text)
    results = []
    
    for line in lines:
        if not line.strip(): continue
        
        # লিস্ট সিম্বল রিমুভ (•, °, :, >)
        clean_line = re.sub(r'[•°:>]', ' ', line).strip()
        
        # নম্বর খোঁজা (১০-১১ ডিজিটের নম্বর যা ০ বা ৮৮ দিয়ে শুরু)
        # আরও শক্তিশালী রেজেক্স যা +88, 880 বা 01 দিয়ে শুরু হওয়া নম্বর ধরতে পারে
        # 01[3-9]\d{8} : 01 দিয়ে শুরু এবং 11 ডিজিট
        # (?:\+?88)?01[3-9]\d{8} : অপশনাল +88 এর পর 01 দিয়ে শুরু 11 ডিজিট
        phones = re.findall(r'(?:\+?88)?(01[3-9]\d{8})', clean_line)
        
        if phones:
            phone = phones[0] # প্রথম ফোন নম্বরটি নেওয়া
            
            # নাম বের করা (লাইন থেকে নম্বরটি বাদ দিলে যা থাকে)
            # রেজেক্স ব্যবহার করে ফোন নম্বরটি রিমুভ করা
            name_part = re.sub(r'(?:\+?88)?(01[3-9]\d{8})', '', clean_line).strip()
            
            if not name_part: name_part = "No Name"
            results.append(create_vcf(name_part, phone))
    
    return "\n".join(results)


# --- নতুন VCF রিডিং ফাংশন ---
def parse_vcf_data(vcf_content):
    contacts = []
    # প্রতিটি VCARD ব্লক আলাদা করা
    vcard_blocks = re.findall(r'BEGIN:VCARD.*?END:VCARD', vcf_content, re.DOTALL)

    for block in vcard_blocks:
        name = "Unknown"
        phone = "Unknown"

        # নাম খোঁজা
        name_match = re.search(r'N:(.*?);;;', block)
        if name_match:
            name = name_match.group(1).strip()
        
        # ফোন নম্বর খোঁজা (TEL;CELL;PREF: অথবা TEL: দিয়ে শুরু হতে পারে)
        phone_match = re.search(r'TEL(?:;CELL)?(?:;PREF)?:([+\d]+)', block)
        if phone_match:
            phone = phone_match.group(1).strip()
        
        contacts.append({"name": name, "phone": phone})
    
    return contacts
