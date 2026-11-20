from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet')
out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\kirino_candidate_spritesheet.webp')
W,H,C,R=192,208,8,11
sheet=Image.new('RGBA',(W*C,H*R),(0,0,0,0))
# Select clean source frames for each native row.
sel={
 0:[('idle',1)]*8,
 1:[('idle',1)]*8,
 2:[('idle',1)]*8,
 3:[('wave',i) for i in range(1,9)],
 4:[('success',i) for i in range(1,7)]+[('success',6),('success',1)],
 5:[('failed',i) for i in range(1,7)]+[('failed',6),('failed',1)],
 6:[('shy',i) for i in range(1,7)]+[('shy',6),('shy',1)],
 7:[('thinking',i) for i in range(1,7)]+[('thinking',6),('thinking',1)],
 8:[('success',i) for i in range(1,7)]+[('success',6),('success',1)],
 9:[('idle',1)]*8,
 10:[('shy',6)]*8,
}
for row,frames in sel.items():
 for col,(state,n) in enumerate(frames):
  src=root/'sprites'/state/f'frame_{n:03d}.png'
  im=Image.open(src).convert('RGBA')
  # Fit artwork to a 178x198 content area, align alpha bbox bottom 201.
  bbox=im.getchannel('A').getbbox()
  if not bbox: continue
  im=im.crop(bbox)
  scale=min(178/im.width,198/im.height)
  im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
  x=(W-im.width)//2
  y=201-im.height
  sheet.alpha_composite(im,(col*W+x,row*H+y))
sheet.save(out,format='WEBP',lossless=True,method=6)
print(out,sheet.size)
