from pathlib import Path
from PIL import Image,ImageDraw
p=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi');im=Image.open(p/'spritesheet.webp').convert('RGBA');W,H=192,208
spec={'failed':(5,8),'waiting':(6,6),'thinking':(7,6),'review':(8,6),'wave':(3,4)}
for name,(row,n) in spec.items():
 fs=[im.crop((i*W,row*H,(i+1)*W,(row+1)*H)) for i in range(n)];render=[]
 for t in range(60):
  pos=t*n/60;i=int(pos)%n;frac=pos-int(pos);frame=Image.blend(fs[i],fs[(i+1)%n],frac);stage=Image.new('RGBA',(W*2,H*2+34),'white');stage.alpha_composite(frame.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34));ImageDraw.Draw(stage).text((10,8),name+' - 60 fps',fill=(35,45,65,255));render.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
 render[0].save(p/(name+'-60fps-preview.gif'),save_all=True,append_images=render[1:],duration=16,loop=0,optimize=False)
print('created',','.join(spec))
