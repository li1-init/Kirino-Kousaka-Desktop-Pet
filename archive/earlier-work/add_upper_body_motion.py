from pathlib import Path
from PIL import Image,ImageDraw
p=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi');atlas=Image.open(p/'spritesheet.webp').convert('RGBA');W,H=192,208
# Feathered mask keeps feet and skirt registration fixed while allowing head, hair, arms, and expression to move.
mask=Image.new('L',(W,H),0);mp=mask.load()
for y in range(H):
 v=255 if y<92 else max(0,min(255,round((145-y)*255/(145-92))))
 for x in range(W):mp[x,y]=v

def moved(base,dx,dy):
 shifted=Image.new('RGBA',(W,H),(0,0,0,0));shifted.alpha_composite(base,(dx,dy));return Image.composite(shifted,base,mask)
patterns={5:[(0,0),(1,0),(1,1),(0,2),(-1,1),(-1,0),(0,-1),(1,0)],7:[(0,0),(1,-1),(1,-2),(0,-1),(-1,0),(-1,1)],8:[(0,0),(1,-1),(1,-2),(0,-1),(-1,0),(-1,1)]}
for row,pattern in patterns.items():
 base=atlas.crop((0,row*H,W,(row+1)*H))
 for col,(dx,dy) in enumerate(pattern):
  atlas.paste(moved(base,dx,dy),(col*W,row*H))
atlas.save(p/'spritesheet.webp',format='WEBP',lossless=True,method=6);atlas.save(p/'spritesheet.png',format='PNG');print('upper-body motion added')
