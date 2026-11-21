from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
root=Path(r'C:\Users\86166\Documents\Codex\kirino-desktop-pet');out=Path(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\outputs\kirino-chibi')
strip=Image.open(root/'assets'/'wave_true_strip.png').convert('RGBA'); a=strip.getchannel('A'); p=a.load(); w,h=strip.size; seen=set(); comps=[]
for y in range(h):
 for x in range(w):
  if p[x,y]<=0 or (x,y) in seen: continue
  q=[(x,y)];seen.add((x,y));pts=[]
  while q:
   cx,cy=q.pop();pts.append((cx,cy))
   for nx,ny in ((cx-1,cy),(cx+1,cy),(cx,cy-1),(cx,cy+1)):
    if 0<=nx<w and 0<=ny<h and (nx,ny) not in seen and p[nx,ny]>0:
     seen.add((nx,ny));q.append((nx,ny))
  if len(pts)>5000:
   xs=[u for u,v in pts];ys=[v for u,v in pts];comps.append((min(xs),min(ys),max(xs),max(ys),pts))
comps=sorted(comps,key=lambda c:c[0])
W,H=192,208;target_h=183;bottom=191;center=99
def component_crop(comp):
 x0,y0,x1,y1,pts=comp; mask=Image.new('L',strip.size,0);mp=mask.load()
 for x,y in pts:mp[x,y]=255
 box=(x0,y0,x1+1,y1+1);src=Image.new('RGBA',strip.size,(0,0,0,0));src.paste(strip,(0,0),mask);return src.crop(box)
def normalize(im):
 scale=target_h/im.height;r=im.resize((round(im.width*scale),target_h),Image.Resampling.LANCZOS);o=Image.new('RGBA',(W,H),(0,0,0,0));o.alpha_composite(r,(round(center-r.width/2),bottom-target_h+1));return o
idle_src=Image.open(root/'sprites'/'idle'/'frame_001.png').convert('RGBA')
# use idle from existing current row 0 to align exact
atlas=Image.open(out/'spritesheet.webp').convert('RGBA');idle=atlas.crop((0,0,W,H))
mask=Image.new('L',(W,H),0);ImageDraw.Draw(mask).ellipse((70,24,128,83),fill=255);mask=mask.filter(ImageFilter.GaussianBlur(2))
frames=[]
for comp in comps[:4]:
 frame=normalize(component_crop(comp));frames.append(Image.composite(idle,frame,mask))
qa=Image.new('RGBA',(W*4,H),'white')
for i,im in enumerate(frames):qa.alpha_composite(im,(i*W,0))
qa.save(r'C:\Users\86166\Documents\Codex\2026-11-19\1-2-3\work\wave_true_clean_row.png')
for i,im in enumerate(frames):atlas.alpha_composite(im,(i*W,3*H))
atlas.save(out/'spritesheet.webp',format='WEBP',lossless=True,method=6);atlas.save(out/'spritesheet.png',format='PNG')
render=[]
for i in range(4):
 a1=frames[i];b=frames[(i+1)%4]
 for step in range(15):
  im=Image.blend(a1,b,step/15);stage=Image.new('RGBA',(W*2,H*2+34),'white');stage.alpha_composite(im.resize((W*2,H*2),Image.Resampling.LANCZOS),(0,34));ImageDraw.Draw(stage).text((10,8),'wave goodbye - 60 fps',fill=(35,45,65,255));render.append(stage.convert('P',palette=Image.Palette.ADAPTIVE))
render[0].save(out/'wave-60fps-preview.gif',save_all=True,append_images=render[1:],duration=16,loop=0,optimize=False)
print('components',[(c[0],c[2],c[4].__len__()) for c in comps[:4]])
