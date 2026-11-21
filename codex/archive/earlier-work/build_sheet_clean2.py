from pathlib import Path
from PIL import Image
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet')
out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\kirino_candidate_spritesheet_clean2.webp')
W,H,C,R=192,208,8,11
sheet=Image.new('RGBA',(W*C,H*R),(0,0,0,0))
# Clean full-frame states. Base art is used for wave because the wave PNGs contain old composite trails.
sel={0:[('idle',1)]*8,1:[('idle',1)]*8,2:[('idle',1)]*8,3:[('base',0)]*8,4:[('success',i) for i in [1,2,3,4,5,6,5,1]],5:[('failed',i) for i in [1,2,3,4,5,6,5,1]],6:[('shy',i) for i in [1,2,3,4,5,6,5,1]],7:[('thinking',i) for i in [1,2,3,4,5,6,5,1]],8:[('success',i) for i in [1,2,3,4,5,6,5,1]],9:[('idle',1)]*8,10:[('shy',6)]*8}
for row,fs in sel.items():
 for col,(state,n) in enumerate(fs):
  src=root/'assets'/'kirino_base.png' if state=='base' else root/'sprites'/state/f'frame_{n:03d}.png'
  im=Image.open(src).convert('RGBA')
  # Force RGB=0 on transparent pixels before resampling to prevent matte-color fringes.
  alpha=im.getchannel('A'); rgba=Image.new('RGBA',im.size,(0,0,0,0)); rgba.paste(im,(0,0),alpha); im=rgba
  bbox=alpha.getbbox()
  if not bbox: continue
  im=im.crop(bbox); scale=min(178/im.width,198/im.height)
  im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
  a=im.getchannel('A'); im.putalpha(a.point(lambda v: 0 if v<18 else v))
  x=(W-im.width)//2; y=201-im.height; sheet.alpha_composite(im,(col*W+x,row*H+y))
sheet.save(out,format='WEBP',lossless=True,method=6)
bg=Image.new('RGBA',sheet.size,(220,220,220,255)); bg.alpha_composite(sheet); bg.convert('RGB').save(out.with_suffix('.png'))
print(out)
