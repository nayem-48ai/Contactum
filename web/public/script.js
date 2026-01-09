document.addEventListener('DOMContentLoaded', () => {
    const textInput = document.getElementById('textInput');
    const convertToVcfBtn = document.getElementById('convertToVcfBtn');
    const textToVcfOutput = document.getElementById('textToVcfOutput');
    const vcfOutputText = document.getElementById('vcfOutputText');
    const downloadVcfBtn = document.getElementById('downloadVcfBtn');

    const vcfFileInput = document.getElementById('vcfFileInput');
    const readVcfBtn = document.getElementById('readVcfBtn');
    const vcfToTextOutput = document.getElementById('vcfToTextOutput');
    const extractedContactsText = document.getElementById('extractedContactsText');
    const downloadTxtBtn = document.getElementById('downloadTxtBtn');

    // --- VCF Utility Functions (Ported from Python) ---

    function formatNumber(numStr) {
        // Bengali to English digits (simplified, adjust if more complex logic needed)
        const bengaliDigits = "০১২৩৪৫৬৭৮৯";
        const englishDigits = "0123456789";
        for (let i = 0; i < bengaliDigits.length; i++) {
            numStr = numStr.replace(new RegExp(bengaliDigits[i], 'g'), englishDigits[i]);
        }

        // Extract only digits
        let cleanNum = numStr.replace(/\D/g, '');

        // Number formatting (simplified for client-side JS)
        if (cleanNum.startsWith('880')) {
            cleanNum = cleanNum.substring(2);
        }
        
        if (cleanNum.startsWith('01') && cleanNum.length === 11) {
            return `+88${cleanNum}`;
        } else if (cleanNum.startsWith('1') && cleanNum.length === 10) { // e.g., 17xxxxxxxx
            return `+880${cleanNum}`;
        } else {
            return numStr; // Return as is if format doesn't match standard
        }
    }

    function createVcf(name, phone) {
        const formattedPhone = formatNumber(phone);
        return `BEGIN:VCARD\nVERSION:2.1\nN:${name};;;\nTEL;CELL;PREF:${formattedPhone}\nEND:VCARD`;
    }

    function processBulk(text) {
        const lines = text.split('\n');
        const results = [];

        lines.forEach(line => {
            if (!line.trim()) return;

            const cleanLine = line.replace(/[•°:>]/g, ' ').trim();
            // Regex to find Bangladesh numbers (01x-xxxx-xxxx or +8801x-xxxx-xxxx)
            const phoneMatch = cleanLine.match(/(?:\+?88)?(01[3-9]\d{8})/);

            if (phoneMatch) {
                const phone = phoneMatch[1]; // Get the 01... number part
                const namePart = cleanLine.replace(phoneMatch[0], '').trim();
                const name = namePart || "No Name";
                results.push(createVcf(name, phone));
            }
        });
        return results.join('\n');
    }

    function parseVcfData(vcfContent) {
        const contacts = [];
        const vcardBlocks = vcfContent.match(/BEGIN:VCARD[\s\S]*?END:VCARD/g);

        if (!vcardBlocks) return contacts;

        vcardBlocks.forEach(block => {
            let name = "Unknown";
            let phone = "Unknown";

            const nameMatch = block.match(/N:(.*?);;;/);
            if (nameMatch) {
                name = nameMatch[1].trim();
            }

            const phoneMatch = block.match(/TEL(?:;CELL)?(?:;PREF)?:([+\d]+)/);
            if (phoneMatch) {
                phone = phoneMatch[1].trim();
            }
            contacts.push({ name, phone });
        });
        return contacts;
    }

    // --- Event Listeners ---

    convertToVcfBtn.addEventListener('click', () => {
        const text = textInput.value;
        const vcfContent = processBulk(text);

        if (vcfContent) {
            vcfOutputText.value = vcfContent;
            textToVcfOutput.classList.remove('hidden');
        } else {
            vcfOutputText.value = "No valid contacts found to generate VCF.";
            textToVcfOutput.classList.remove('hidden');
        }
    });

    downloadVcfBtn.addEventListener('click', () => {
        const vcfContent = vcfOutputText.value;
        if (vcfContent) {
            const blob = new Blob([vcfContent], { type: 'text/vcard;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'contacts.vcf';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
        }
    });

    readVcfBtn.addEventListener('click', () => {
        const file = vcfFileInput.files[0];
        if (!file) {
            alert('Please select a VCF file.');
            return;
        }

        const reader = new FileReader();
        reader.onload = (e) => {
            const vcfContent = e.target.result;
            const contacts = parseVcfData(vcfContent);

            if (contacts.length > 0) {
                let outputText = "";
                contacts.forEach(contact => {
                    outputText += `Name: ${contact.name}\nPhone: ${contact.phone}\n---\n`;
                });
                extractedContactsText.value = outputText;
                vcfToTextOutput.classList.remove('hidden');
            } else {
                extractedContactsText.value = "No contacts could be extracted from this VCF file.";
                vcfToTextOutput.classList.remove('hidden');
            }
        };
        reader.onerror = () => {
            alert('Failed to read file.');
        };
        reader.readAsText(file);
    });

    downloadTxtBtn.addEventListener('click', () => {
        const textContent = extractedContactsText.value;
        if (textContent) {
            const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'extracted_contacts.txt';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
        }
    });
});
