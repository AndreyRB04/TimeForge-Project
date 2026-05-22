content = open('timeforge_backend/settings.py', 'rb').read()
for i, b in enumerate(content):
    if b > 127:
        print(i, hex(b), content[i-10:i+10])