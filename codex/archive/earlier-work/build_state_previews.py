from pathlib import Path
from PIL import Image,ImageDraw
atlas=Image.open(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi\spritesheet.webp').convert('RGBA')
W,H=192,208
states={'failed':(5,8),'waiting':(6,6),'thinking':(7,6),'review':(8,6)}
out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\state_previews');out.mkdir(parents=True,exist_ok=True)
for name,(row,count) in states.items():
 keyframes=[atlas.crop((i*W,row*H,(i+1)*W,(row+1)*H)) for i in range(count)]
 rendered=[]
 substeps=8
 for i,a in enumerate(keyframes):
  b=keyframes[(i+1)%count]
  for step in range(substeps):
   t=step/substeps
   blended=Image.blend(a,b,t)
   stage=Image.new('RGBA',(W*2,H*2+34),'white')
   stage.alpha_composite(blended.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34))
   ImageDraw.Draw(stage).text((10,8),f'{name} - 60 fps',fill=(35,45,65,255))
   rendered.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
 rendered[0].save(out/f'{name}-60fps.gif',save_all=True,append_images=rendered[1:],duration=16,loop=0,optimize=False)
 # create keyframe contact strip
 strip=Image.new('RGBA',(W*count,H),'white')
 for i,frame in enumerate(keyframes): strip.alpha_composite(frame,(i*W,0))
 strip.save(out/f'{name}-keyframes.png')
 # report pairwise changes and bbox
 diff=[]
 for i,a in enumerate(keyframes):
  b=keyframes[(i+1)%count]
  # mean RGBA diff on visible composite
  aa=Image.new('RGBA',(W,H),'white'); aa.alpha_composite(a)
  bb=Image.new('RGBA',(W,H),'white'); bb.alpha_composite(b)
  diff.append(sum(abs(x-y) for x,y in zip(aa.convert('RGB').tobytes(),bb.convert('RGB').tobytes()))/(W*H*3))
 print(name,'frames',count,'mean_pair_diffs',[round(v,2) for v in diff])
