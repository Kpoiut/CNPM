import re
content = open(r'c:\Users\Admin\Documents\real-estate-avm\src\backend\main.py','r',encoding='utf-8').read()
matches = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)', content)
for m in matches:
    print(f"{m[0].upper():6s} {m[1]}")
