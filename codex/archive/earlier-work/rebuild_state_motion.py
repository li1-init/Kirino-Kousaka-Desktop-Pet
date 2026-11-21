from pathlib import Path
from PIL import Image,ImageDraw
from statistics import median
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet');out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi');W,H=192,208;TH=183;B=191;C=99

def largest(im):
 a=im.getchannel('A');p=a.load();w,h=im.size;seen=set();best=[]
 for y in range(h):
  for x in range(w):
   if p[x,y]<=0 or (x,y) in seen:continue
   q=[(x,y)];seen.add((x,y));pts=[]
   while q:
    cx,cy=q.pop();pts.append((cx,cy))
    for nx,ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
     if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and p[nx,ny]>0:seen.add((nx,ny));q.append((nx,ny))
   if len(pts)>len(best):best=pts
 mask=Image.new('L',(w,h),0);mp=mask.load()
 for x,y in best:mp[x,y]=255
 box=mask.getbbox();o=Image.new('RGBA',(w,h),(0,0,0,0));o.paste(im,(0,0),mask);return o.crop(box)
def prepare(state,seq):
 raw=[largest(Image.open(f).convert('RGBA')) for f in sorted((root/'sprites'/state).glob('frame_*.png'))];m=median([x.height for x in raw]);res=[]
 for i in seq:
  c=raw[i];s=TH/m;r=c.resize((round(c.width*s),round(c.height*s)),Image.Resampling.LANCZOS);o=Image.new('RGBA',(W,H),(0,0,0,0));o.alpha_composite(r,(round(C-r.width/2),B-r.height));res.append(o)
 return res
atlas=Image.open(out/'spritesheet.webp').convert('RGBA');spec={'failed':(5,[0,1,2,3,4,5,4,3]),'waiting':(6,[0,1,2,3,4,5]),'thinking':(7,[0,1,2,3,4,5]),'review':(8,[0,1,2,3,4,5])}
for name,(row,seq) in spec.items():
 fs=prepare('shy' if name=='waiting' else ('success' if name=='review' else name),seq)
 for col,fr in enumerate(fs):atlas.paste(fr,(col*W,row*H),fr)
 render=[];n=len(fs)
 for t in range(60):
  pos=t*n/60;i=int(pos)%n;fr=pos-int(pos);im=Image.blend(fs[i],fs[(i+1)%n],fr);stage=Image.new('RGBA',(W*2,H*2+34),'white');stage.alpha_composite(im.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34));ImageDraw.Draw(stage).text((10,8),name+' - 60 fps',fill=(35,45,65,255));render.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
 render[0].save(out/(name+'-60fps-preview.gif'),save_all=True,append_images=render[1:],duration=16,loop=0,optimize=False)
atlas.save(out/'spritesheet.webp',format='WEBP',lossless=True,method=6);atlas.save(out/'spritesheet.png',format='PNG');print('done')
