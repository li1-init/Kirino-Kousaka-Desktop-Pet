from pathlib import Path
from PIL import Image,ImageDraw
p=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi');im=Image.open(p/'spritesheet.webp').convert('RGBA');W,H=192,208;req=[6,8,8,4,5,8,6,6,6,8,8];labels=['idle','move-r','move-l','wave','jump','failed','waiting','thinking','review','look1','look2'];c=Image.new('RGBA',im.size,'white');d=ImageDraw.Draw(c)
for row,count in enumerate(req):
 for col in range(count):c.alpha_composite(im.crop((col*W,row*H,(col+1)*W,row*H+H)),(col*W,row*H))
 d.rectangle((2,row*H+2,180,row*H+28),fill=(38,48,68,220));d.text((8,row*H+7),labels[row],fill='white')
 for col in range(9):d.line((col*W,row*H,col*W,(row+1)*H),fill=(80,100,120,80),width=1)
 d.line((0,row*H,im.width,row*H),fill=(80,100,120,110),width=1)
c.save(p/'contact-sheet.png')
