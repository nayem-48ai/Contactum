document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('textInput');
    const createVcfBtn = document.getElementById('createVcfBtn');
    const downloadLink = document.getElementById('downloadLink');

    const vcfFileInput = document.getElementById('vcfFileInput');
    const readVcfBtn = document.getElementById('readVcfBtn');
    const vcfOutput = document.getElementById('vcfOutput');
    const vcfContentPre = document.getElementById('vcfContent');

    // Utility functions (mirrored from Python, adapted for JS)
    function formatNumberJS(numStr) {
        const bengaliDigits = "০১২৩৪৫৬৭৮৯";
        const englishDigits = "0123456789";
        for (let i = 0; i < bengaliDigits.length; i++) {
            numStr = numStr.replace(new RegExp(bengaliDigits[i], 'g'), englishDigits[i]);
        }
        let cleanNum = numStr.replace(/\D/g, ''); // Remove non-digits
        
        if (cleanNum.startsWith('880')) {
            cleanNum = cleanNum.substring(2); // Remove '88'
        }
        if (cleanNum.startsWith('0')) {
            return `+88${cleanNum}`;
        } else {
            return `+880${cleanNum}`;
        }
    }

    function createVcfStringJS(name, phone) {
        const formattedPhone = formatNumberJS(phone);
        return `BEGIN:VCARD\nVERSION:2.1\nN:${name};;;\nTEL;CELL;PREF:${formattedPhone}\nEND:VCARD`;
    }

    function processTextToVcfBulkJS(text) {
        const lines = text.split('\n');
        const results = [];
        const phoneRegex = /(?:\+?88)?01[3-9]\d{8}/; // Matches BD numbers

        for (const line of lines) {
            if (!line.trim()) continue;
            let cleanLine = line.replace(/[•°:>]/g, ' ').trim();
            const phoneMatch = cleanLine.match(phoneRegex);

            if (phoneMatch) {
                const phone = phoneMatch[0];
                let name = cleanLine.replace(phone, '').trim();
                if (!name) name = "No Name";
                results.push(createVcfStringJS(name, phone));
            }
        }
        return results.join('\n');
    }

    // --- Reverse VCF functions (for client-side parsing) ---
    function parseVcfStringJS(vcfContent) {
        const contacts = [];
        let currentContact = {};
        const lines = vcfContent.split('\n');

        for (const line of lines) {
            if (line.startsWith("BEGIN:VCARD")) {
                currentContact = {};
            } else if (line.startsWith("N:")) {
                const parts = line.substring(2).split(';');
                const firstName = parts.length > 1 ? parts[1] : "";
                const lastName = parts.length > 0 ? parts[0] : "";
                currentContact.name = `${firstName} ${lastName}`.trim();
            } else if (line.startsWith("TEL;")) {
                const match = line.match(/\d+/); // Find first sequence of digits
                if (match) {
                    currentContact.phone = match[0];
                }
            } else if (line.startsWith("END:VCARD")) {
                if (currentContact.name && currentContact.phone) {
                    contacts.push(currentContact);
                }
                currentContact = {}; // Reset for next contact
            }
        }
        return contacts;
    }

    // Event Listeners
    createVcfBtn.addEventListener('click', () => {
        const inputText = textInput.value;
        const vcfContent = processTextToVcfBulkJS(inputText);

        if (vcfContent) {
            const blob = new Blob([vcfContent], { type: 'text/vcard;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            downloadLink.href = url;
            downloadLink.style.display = 'block';
            downloadLink.textContent = 'contacts.vcf ডাউনলোড করুন';
        } else {
            alert("কোনো কন্টাক্ট পাওয়া যায়নি।");
            downloadLink.style.display = 'none';
        }
    });

    readVcfBtn.addEventListener('click', () => {
        const file = vcfFileInput.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (e) => {
                const vcfText = e.target.result;
                const contacts = parseVcfStringJS(vcfText);

                if (contacts.length > 0) {
                    let outputHtml = '';
                    contacts.forEach(contact => {
                        outputHtml += `নাম: ${contact.name || 'N/A'}, ফোন: ${contact.phone || 'N/A'}\n`;
                    });
                    vcfContentPre.textContent = outputHtml;
                    vcfOutput.style.display = 'block';
                } else {
                    vcfContentPre.textContent = "VCF ফাইল থেকে কোনো কন্টাক্ট পড়া যায়নি।";
                    vcfOutput.style.display = 'block';
                }
            };
            reader.readAsText(file);
        } else {
            alert("একটি VCF ফাইল নির্বাচন করুন।");
            vcfOutput.style.display = 'none';
        }
    });
});
