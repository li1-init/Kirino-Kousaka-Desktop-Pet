from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi'); wave=Image.open(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\kirino_wave_motion_candidate.webp').convert('RGBA'); atlas=Image.open(out/'spritesheet.webp').convert('RGBA'); W,H=192,208
# The candidate row is clean, but clear the old row before placing it.
atlas.paste((0,0,0,0),(0,3*H,8*W,4*H))
for i in range(4): atlas.alpha_composite(wave.crop((i*W,3*H,(i+1)*W,4*H)),(i*W,3*H))
atlas.save(out/'spritesheet.webp',format='WEBP',lossless=True,method=6);atlas.save(out/'spritesheet.png',format='PNG')
# rebuild 60fps preview from clean row
frames=[atlas.crop((i*W,3*H,(i+1)*W,4*H)) for i in range(4)];render=[]
for i in range(4):
 a=frames[i];b=frames[(i+1)%4]
 for step in range(15):
  im=Image.blend(a,b,step/15);stage=Image.new('RGBA',(W*2,H*2+34),'white');stage.alpha_composite(im.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34));ImageDraw.Draw(stage).text((10,8),'wave goodbye - 60 fps',fill=(35,45,65,255));render.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
render[0].save(out/'wave-60fps-preview.gif',save_all=True,append_images=render[1:],duration=16,loop=0,optimize=False)
