"""Source-sized Korean candidates; no game/archive installation.

The user approved the source-pixel cleanup/typesetting workflow after reviewing
the image-generated mockups. Generated mockup pixels are not used here.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(r'P:\AI\Codex\projects\fault-stp-lightkravte-asset-review-2026-09-04')
OUT=ROOT/'production_2026-09-08'
FONT=Path(r'C:\Windows\Fonts\NotoSansKR-VF.ttf')
SERIF=Path(r'C:\Windows\Fonts\NotoSerifKR-VF.ttf')
SPECS={
 'anime dmitry': [('DMITRY ZHUKOV','드미트리 주코프','name')],
 'anime hare': [('CHARACTER ANIMATOR','캐릭터 애니메이터','role'),('HARE KONATSU','하레 코나츠','name')],
 'Dmitry_c': [('ENVIRONMENTAL ANIMATION BY','환경 애니메이션','role'),('DMITRY ZHUKOV','드미트리 주코프','name')],
 'Kawamura_C': [('AZUSA KAWAMURA','아즈사 카와무라','name')],
 'Misaki_C': [('LEAD CHARACTER ANIMATOR','수석 캐릭터 애니메이터','role'),('MISAKI EYMARD','미사키 에마르','name')],
 'Munisix_C': [('FAULT SERIES CREATED BY','fault 시리즈 원작','role'),('MUNISIX','무니식스','name')],
 'Nyantastic_C': [('MORALE OFFICERS','사기 진작 담당','role'),('THE NYANTASTIC TRIO','더 냥타스틱 트리오','name')],
 'Oda_C': [('NARIHISA ODA','나리히사 오다','name')],
 'Sakamoto_c': [('PHOENIXX INC',None,'preserve'),('KAZUNORI SAKAMOTO','카즈노리 사카모토','name')],
}

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fnt(size,weight=400,serif=False):
 f=ImageFont.truetype(str(SERIF if serif else FONT),size)
 try:f.set_variation_by_axes([weight])
 except (OSError,ValueError,AttributeError):pass
 return f
def bbox(mask):
 ys,xs=np.where(mask)
 return [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
def text_ink(text,height,maxw,kind):
 scale=3; font=fnt(round(height*1.22*scale),650 if kind=='name' else 400)
 w=int(font.getlength(text))+200; h=int(height*2.2*scale)
 layer=Image.new('RGBA',(w,h));d=ImageDraw.Draw(layer)
 b=d.textbbox((0,0),text,font=font,stroke_width=scale)
 x=10-b[0];y=10-b[1]
 d.text((x+scale,y+2*scale),text,font=font,fill=(30,30,30,210),stroke_width=scale,stroke_fill=(30,30,30,210))
 d.text((x,y),text,font=font,fill=(250,250,250,255),stroke_width=0)
 layer=layer.crop(layer.getbbox())
 ratio=min(height/layer.height,maxw/layer.width)
 return layer.resize((round(layer.width*ratio),round(layer.height*ratio)),Image.Resampling.LANCZOS)
def preview(im,bg=(24,24,27,255)):
 base=Image.new('RGBA',im.size,bg);base.alpha_composite(im);return base.convert('RGB')

def exemplar_restore(a,mask):
 """Copy real unmasked same-state donor patches, never diffuse/blend glyph shapes.

 Only the source-owned holes are writable. Patch matching includes alpha so
 transparent brush holes and dry-brush texture are carried with their pigment.
 """
 r=6; k=r*2+1
 src=cv2.copyMakeBorder(a,r,r,r,r,cv2.BORDER_REFLECT_101)
 missing=np.pad(mask>0,r,constant_values=False)
 initial=missing.copy();dst=src.copy()
 valid=cv2.erode((~initial).astype(np.uint8),np.ones((k,k),np.uint8)).astype(bool)
 valid[:r]=False;valid[-r:]=False;valid[:,:r]=False;valid[:,-r:]=False
 # Use alpha and premultiplied luminance, avoiding invisible RGB matte noise.
 def features(im):
  alpha=im[:,:,3].astype(np.float32)/255
  lum=cv2.cvtColor(im[:,:,:3],cv2.COLOR_RGB2GRAY).astype(np.float32)
  return np.stack([lum*alpha,alpha*255],axis=2)
 sfeat=features(src)
 step=0
 while missing.any():
  known=(~missing).astype(np.float32)
  score=cv2.boxFilter(known,-1,(k,k),normalize=False)
  score[~missing]=-1;score[:r]=-1;score[-r:]=-1;score[:,:r]=-1;score[:,-r:]=-1
  y,x=np.unravel_index(score.argmax(),score.shape)
  y0,y1=y-r,y+r+1;x0,x1=x-r,x+r+1
  km=~missing[y0:y1,x0:x1]
  target=features(dst[y0:y1,x0:x1])
  sy0=max(r,y-90);sy1=min(src.shape[0]-r,y+91)
  sx0=max(r,x-160);sx1=min(src.shape[1]-r,x+161)
  candidates=valid[sy0:sy1,sx0:sx1]
  if not candidates.any():sy0=r;sy1=src.shape[0]-r;sx0=r;sx1=src.shape[1]-r;candidates=valid[sy0:sy1,sx0:sx1]
  costs=cv2.matchTemplate(sfeat[sy0-r:sy1+r,sx0-r:sx1+r],target,cv2.TM_SQDIFF,mask=np.repeat(km[:,:,None],2,axis=2).astype(np.float32))
  costs/=max(1,int(km.sum()))
  yy,xx=np.ogrid[sy0:sy1,sx0:sx1]
  costs+=0.02*((yy-y)**2+(xx-x)**2)
  costs[~candidates]=np.inf
  dy,dx=np.unravel_index(np.argmin(costs),costs.shape);dy+=sy0;dx+=sx0
  owned=~km
  dst[y0:y1,x0:x1][owned]=src[dy-r:dy+r+1,dx-r:dx+r+1][owned]
  missing[y0:y1,x0:x1][owned]=False
  step+=1
 return dst[r:-r,r:-r]

def save_asset(name,source,clean,owned,layer,meta):
 folder=OUT/'textures'/name;folder.mkdir(parents=True,exist_ok=True)
 a=np.array(source); c=np.array(clean); mask=np.asarray(owned)>0
 final=Image.alpha_composite(clean,layer)
 source.save(folder/'source.png');clean.save(folder/'clean_plate.png')
 Image.fromarray((mask*255).astype('uint8')).save(folder/'source_glyph_mask.png')
 layer.save(folder/'korean_layer.png');final.save(folder/'ko.png')
 aa=np.array(Image.open(folder/'ko.png')); ink=np.array(layer)[:,:,3]>0
 diff=np.any(a!=aa,axis=2); protected=int(np.count_nonzero(diff&~(mask|ink)))
 clean_diff=int(np.count_nonzero(np.any(a!=c,axis=2)&~mask))
 ib=bbox(ink); no_clip=ib is not None and ib[0]>0 and ib[1]>0 and ib[2]<source.width and ib[3]<source.height
 p=Image.new('RGB',(source.width,source.height*3+96),(24,24,27));d=ImageDraw.Draw(p)
 for i,(label,img) in enumerate([('SOURCE',source),('CLEAN PLATE',clean),('KOREAN',final)]):
  top=i*(source.height+32);d.text((8,top+4),label,font=fnt(18),fill='white');p.paste(preview(img),(0,top+32))
 p.save(folder/'comparison.png')
 return dict(meta,name=name,width=source.width,height=source.height,mode=source.mode,source_sha256=sha(folder/'source.png'),output_sha256=sha(folder/'ko.png'),source_glyph_bounds=bbox(mask),target_ink_bounds=ib,outside_owned_pixel_diff=protected,clean_outside_mask_diff=clean_diff,geometry_pass=aa.shape==a.shape,no_clipping=no_clip,visual_status='PENDING_REVIEW',output=str(folder/'ko.png'),comparison=str(folder/'comparison.png'))

def credits():
 entries=json.loads((ROOT/'raster_review/review_targets/manifest.json').read_text(encoding='utf-8'))
 rows=[]
 for e in entries:
  if e['name'] not in SPECS:continue
  src=Image.open(e['png']).convert('RGBA');a=np.array(src)
  # Whole source white face + anti-aliased fringe; expand for dark 1px outlines.
  rgb=a[:,:,:3].astype(np.int16)
  face=(rgb.min(2)>135)&((rgb.max(2)-rgb.min(2))<65)&(a[:,:,3]>0)
  ys=np.where(face.sum(axis=1)>3)[0];runs=[]
  for y in ys:
   if not runs or y>runs[-1][-1]+5:runs.append([y])
   else:runs[-1].append(y)
  specs=SPECS[e['name']]
  if len(runs)!=len(specs):raise ValueError((e['name'],len(runs),len(specs)))
  owned=np.zeros(a.shape[:2],np.uint8);lineinfo=[]
  for run,(en,ko,kind) in zip(runs,specs):
   fm=np.zeros_like(owned);fm[run[0]:run[-1]+1]=face[run[0]:run[-1]+1]*255
   box=bbox(fm);lineinfo.append({'source':en,'ko':ko,'kind':kind,'source_box':box})
   # The original lettering includes a bevel/extruded grey shadow beyond the
   # white face. Its measured reach is up to 6px; retain a source-owned 8px rim.
   if ko:owned|=cv2.dilate(fm,np.ones((17,17),np.uint8))
  # Texture-owned restorations only: RGB and alpha use the immediate same-state
  # source boundary, not a generated lookalike. Persist and visually audit the plate.
  cache=OUT/'plate_cache';cache.mkdir(exist_ok=True)
  key=hashlib.sha256(a.tobytes()+owned.tobytes()+b'exemplar-v1').hexdigest()
  cp=cache/(key+'.png')
  if cp.exists():clean=np.array(Image.open(cp))
  else:
   print('restoring',e['name'],flush=True)
   clean=exemplar_restore(a,owned);Image.fromarray(clean).save(cp)
  layer=Image.new('RGBA',src.size)
  for line in lineinfo:
   if line['ko'] is None:continue
   x0,y0,x1,y1=line['source_box'];height=y1-y0
   ink=text_ink(line['ko'],height+2,src.width-x0-16,line['kind'])
   layer.alpha_composite(ink,(x0,y0-1))
  rows.append(save_asset(e['name'].replace(' ','_'),src,Image.fromarray(clean),owned,layer,{'asset':e['asset'],'path_id':e['path_id'],'source_file':e['png'],'lines':lineinfo,'restoration':'source-derived glyph mask + local same-state boundary reconstruction; hidden pixels are reconstructed, not claimed recovered exactly'}))
 return rows

def splashes():
 rows=[];orig=ROOT/'raster_review/original'
 src=Image.open(orig/'sharedassets0__13__splash_aero_txt_jp.png').convert('RGBA');a=np.array(src)
 mask=a[:,:,3]>0;clean=a.copy();clean[mask]=0
 layer=Image.new('RGBA',src.size)
 lines=['본 기록은 ALICE IN DISSONANCE가','루젠하이드에서 일어난 일을 관찰하고 편집한 것입니다.']
 # Match source text's visual center, while retaining exact source canvas.
 b=bbox(mask);cy=(b[1]+b[3])/2
 for y,t in zip([round(cy-48),round(cy+8)],lines):
  ink=text_ink(t,36,src.width-100,'role');layer.alpha_composite(ink,((src.width-ink.width)//2,y))
 rows.append(save_asset('splash_aero_txt_jp',src,Image.fromarray(clean),mask,layer,{'path_id':13,'source_file':str(orig/'sharedassets0__13__splash_aero_txt_jp.png'),'lines':lines,'restoration':'text-only transparent layer; all nontransparent source pixels are glyph-owned','locale_gate':'ko only'}))
 src=Image.open(orig/'sharedassets0__21__AiD_Splash_2022.png').convert('RGBA');a=np.array(src)
 rgb=a[:,:,:3];mask=(rgb.max(2)>30).astype(np.uint8)*255
 # Text appears in three known blocks; dim background silhouette is protected.
 roi=np.zeros(mask.shape,np.uint8);roi[310:450,300:1620]=255;roi[510:620,60:1860]=255;roi[720:835,500:1450]=255
 mask=cv2.dilate(mask&roi,np.ones((5,5),np.uint8))
 clean=a.copy()
 for c in range(3):clean[:,:,c]=cv2.inpaint(a[:,:,c],mask,3,cv2.INPAINT_TELEA)
 layer=Image.new('RGBA',src.size);d=ImageDraw.Draw(layer)
 lines=['이 이야기는 현재로서는 허구입니다.','실존하는 개인 및 단체와는 아직 아무런 관련이 없습니다.']
 for y,t in zip([470,532],lines):
  ft=fnt(38,400,True);d.text(((src.width-d.textlength(t,font=ft))/2,y),t,font=ft,fill=(242,242,242,255))
 rows.append(save_asset('AiD_Splash_2022',src,Image.fromarray(clean),mask,layer,{'path_id':21,'source_file':str(orig/'sharedassets0__21__AiD_Splash_2022.png'),'lines':lines,'restoration':'all three source text blocks; preserve dim silhouette outside source-derived glyph mask','locale_gate':'ko only','variant':'B Korean-only, original languages use unmodified source'}))
 return rows

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=credits()+splashes()
 report={'created_at':datetime.now(timezone.utc).isoformat(),'translator_model':'Codex internal','thread_id':'019f98c4-2d2a-7502-b05c-6a79321fe89e','model_identity':'Codex GPT-5.5 (session developer identity; not an API trace)','delivery':'source-sized review candidates, not installed','font_sha256':sha(FONT),'assets':rows}
 (OUT/'texture_manifest.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 shutil.copy2(__file__,OUT/'build_credit_assets.py')
 for r in rows:print(r['name'],r['width'],r['height'],r['outside_owned_pixel_diff'],r['no_clipping'])

if __name__=='__main__':main()
