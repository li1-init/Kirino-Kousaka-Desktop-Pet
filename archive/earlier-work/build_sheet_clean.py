from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet')
out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\kirino_candidate_spritesheet_clean.webp')
W,H,C,R=192,208,8,11
sheet=Image.new('RGBA',(W*C,H*R),(0,0,0,0))
sel={0:[('idle',1)]*8,1:[('idle',1)]*8,2:[('idle',1)]*8,3:[('wave',i) for i in range(1,9)],4:[('success',i) for i in range(1,7)]+[('success',6),('success',1)],5:[('failed',i) for i in range(1,7)]+[('failed',6),('failed',1)],6:[('shy',i) for i in range(1,7)]+[('shy',6),('shy',1)],7:[('thinking',i) for i in range(1,7)]+[('thinking',6),('thinking',1)],8:[('success',i) for i in range(1,7)]+[('success',6),('success',1)],9:[('idle',1)]*8,10:[('shy',6)]*8}
for row,fs in sel.items():
 for col,(state,n) in enumerate(fs):
  im=Image.open(root/'sprites'/state/f'frame_{n:03d}.png').convert('RGBA')
  # remove RGB data wherever alpha is zero before any resampling
  px=im.load()
  for y in range(im.height):
   for x in range(im.width):
    if px[x,y][3]==0: px[x,y]=(0,0,0,0)
  bbox=im.getchannel('A').getbbox()
  if not bbox: continue
  im=im.crop(bbox); scale=min(178/im.width,198/im.height)
  im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
  # clean near-zero alpha pixels again to avoid colored halos
  a=im.getchannel('A'); im.putalpha(a.point(lambda v: 0 if v<12 else v))
  x=(W-im.width)//2; y=201-im.height; sheet.alpha_composite(im,(col*W+x,row*H+y))
sheet.save(out,format='WEBP',lossless=True,method=6)
bg=Image.new('RGBA',sheet.size,(220,220,220,255)); bg.alpha_composite(sheet); bg.convert('RGB').save(out.with_suffix('.png'))
print(out)
