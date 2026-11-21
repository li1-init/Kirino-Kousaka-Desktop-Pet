from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet'); out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi')
strip=Image.open(root/'assets'/'wave_return_12frame_strip.png').convert('RGBA')
W,H=192,208; target_h=183; bottom=191; center=99

def largest(im):
 a=im.getchannel('A');p=a.load();w,h=im.size;seen=set();best=[]
 for y in range(h):
  for x in range(w):
   if p[x,y]<=0 or (x,y) in seen: continue
   q=[(x,y)];seen.add((x,y));pts=[]
   while q:
    cx,cy=q.pop();pts.append((cx,cy))
    for nx,ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
     if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and p[nx,ny]>0:
      seen.add((nx,ny));q.append((nx,ny))
   if len(pts)>len(best):best=pts
 mask=Image.new('L',(w,h),0);mp=mask.load()
 for x,y in best:mp[x,y]=255
 box=mask.getbbox();clean=Image.new('RGBA',(w,h),(0,0,0,0));clean.paste(im,(0,0),mask);return clean.crop(box)
def normalize(im):
 c=largest(im);scale=target_h/c.height;r=c.resize((round(c.width*scale),target_h),Image.Resampling.LANCZOS);cell=Image.new('RGBA',(W,H),(0,0,0,0));cell.alpha_composite(r,(round(center-r.width/2),bottom-target_h+1));return cell
idle=normalize(Image.open(root/'sprites'/'idle'/'frame_001.png').convert('RGBA'))
mask=Image.new('L',(W,H),0);ImageDraw.Draw(mask).ellipse((70,24,128,83),fill=255);mask=mask.filter(ImageFilter.GaussianBlur(2))
frames=[]
for i in range(12):
 x0=round(i*strip.width/12);x1=round((i+1)*strip.width/12);cell=normalize(strip.crop((x0,0,x1,strip.height)));frames.append(Image.composite(idle,cell,mask))
qa=Image.new('RGBA',(W*6,H*2),'white')
for i,im in enumerate(frames):qa.alpha_composite(im,((i%6)*W,(i//6)*H))
qa.save(Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\wave_return_12_neutral.png'))
preview=[]
for i in range(12):
 a=frames[i];b=frames[(i+1)%12]
 for step in range(5):preview.append(Image.blend(a,b,step/5))
render=[]
for im in preview:
 stage=Image.new('RGBA',(W*2,H*2+34),'white');stage.alpha_composite(im.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34));ImageDraw.Draw(stage).text((10,8),'wave goodbye - 60 fps',fill=(35,45,65,255));render.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
render[0].save(out/'wave-60fps-preview.gif',save_all=True,append_images=render[1:],duration=16,loop=0,optimize=False)
atlas=Image.open(out/'spritesheet.webp').convert('RGBA')
# low -> middle -> high -> middle
for col,idx in enumerate((11,6,0,6)):atlas.alpha_composite(frames[idx],(col*W,3*H))
atlas.save(out/'spritesheet.webp',format='WEBP',lossless=True,method=6);atlas.save(out/'spritesheet.png',format='PNG')
print('done',len(frames),len(render))
