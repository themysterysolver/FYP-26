#!/usr/bin/env python3
import zipfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}

def extract_text_from_docx(docx_path):
    text_parts = []
    try:
        with zipfile.ZipFile(docx_path, 'r') as z:
            xml_content = z.read('word/document.xml')
    except KeyError:
        return "Error: word/document.xml not found"
    except zipfile.BadZipFile:
        return "Error: Not a valid docx"
    root = ET.fromstring(xml_content)
    for elem in root.iter():
        if elem.tag.endswith('}p') or elem.tag.endswith('}tc'):
            para_text = []
            for t in elem.iter():
                if t.tag.endswith('}t'):
                    if t.text: para_text.append(t.text)
                    if t.tail: para_text.append(t.tail)
            s = ''.join(para_text).strip()
            if s: text_parts.append(s)
    return chr(10).join(text_parts)

def get_chapter3_structure(text):
    lines = text.split(chr(10))
    structure = []
    in_ch3 = False
    for line in lines:
        if re.search(r'CHAPTER\s+3|Chapter\s+3', line, re.I):
            in_ch3 = True
            structure.append(line.strip())
        elif in_ch3:
            if re.search(r'CHAPTER\s+[4-9]|Chapter\s+[4-9]', line, re.I):
                break
            stripped = line.strip()
            if stripped and (re.match(r'3\.\d', stripped) or re.match(r'\d+\.\d+', stripped) or (len(stripped)<80 and stripped.isupper())):
                structure.append(stripped)
    return structure

def get_system_overview(text):
    lines = text.split(chr(10))
    result = []
    in_section = False
    for line in lines:
        if re.search(r'System\s+Overview', line, re.I):
            in_section = True
            result.append(line)
        elif in_section:
            if re.match(r'^\d+\.\s+[A-Z]', line) or re.match(r'^\d+\.\d+', line):
                if not re.search(r'System\s+Overview', line, re.I):
                    break
            result.append(line)
    return chr(10).join(result) if result else None

base = Path(__file__).parent
thesis_path = base / 'thesis.docx'
draft_path = base / 'Team-38 thesis_rough draft.docx'

print('Extracting thesis.docx...')
thesis_text = extract_text_from_docx(thesis_path)
(base / 'extracted_thesis.txt').write_text(thesis_text, encoding='utf-8')
print('Saved extracted_thesis.txt')

print('Extracting draft...')
draft_text = extract_text_from_docx(draft_path)
(base / 'extracted_draft.txt').write_text(draft_text, encoding='utf-8')
print('Saved extracted_draft.txt')

ch3 = get_chapter3_structure(thesis_text)
print('--- Chapter 3 Structure ---')
for h in ch3[:40]:
    print(h)

sys_ov = get_system_overview(draft_text)
print('--- System Overview ---')
print((sys_ov[:3500] if sys_ov else 'Not found'))
