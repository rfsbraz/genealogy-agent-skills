"""Bind crops to pinned source-page pixels; semantic target choice remains a visual check."""
import hashlib
from pathlib import Path
import shutil


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def page_key(source_id, page):
    return (source_id, str(page))


class SourcePages:
    def __init__(self, records, base, stage, image_tools):
        if not isinstance(records,list) or not records:
            raise ValueError('Packet schema 1.2 requires pages: pinned original page images, hashes and locators.')
        from PIL import Image
        self.base,self.stage=Path(base),Path(stage)
        self.pages={};self.crops={};self.images={}
        (self.stage/'sources').mkdir()
        (self.stage/'crops').mkdir()
        for row in records:
            if not isinstance(row,dict) or any(not isinstance(row.get(k),str) or not row[k].strip() for k in ('source_id','image','sha256','source_locator')):
                raise ValueError('Each page needs source_id, page, image, sha256 and source_locator.')
            page=row.get('page')
            if isinstance(page,bool) or not ((isinstance(page,int) and page>0) or (isinstance(page,str) and page.strip())):
                raise ValueError('Invalid physical page identity.')
            key=page_key(row['source_id'],page)
            if key in self.pages:raise ValueError('Duplicate source/page registration.')
            path=self.base/row['image']
            if not path.is_file():raise ValueError('Missing original page: '+str(path))
            dest=Path('sources')/('page-'+str(len(self.pages)+1).zfill(3)+path.suffix.lower())
            shutil.copyfile(path,self.stage/dest)
            # Verify the frozen bytes, then decode only that snapshot. The external
            # source can change during copying without changing the pinned hash.
            if digest(self.stage/dest)!=row['sha256']:raise ValueError('Original page hash mismatch.')
            size=image_tools.image_info(self.stage/dest)
            with Image.open(self.stage/dest) as im:
                if im.mode not in ('1','L','LA','P','RGB','RGBA'):
                    raise ValueError('Unsupported source image mode: '+im.mode+'. Preserve the original and prepare a documented 8-bit display page; do not clip high-depth ink.')
                self.images[key]=im.convert('RGBA')
            self.pages[key]={k:row[k] for k in ('source_id','page','sha256','source_locator')}
            self.pages[key].update(file=dest.as_posix(),dimensions=list(size))

    def crop(self, record):
        from PIL import Image
        key=page_key(record['source_id'],record['page'])
        if key not in self.pages:raise ValueError('Crop refers to an unregistered source/page.')
        if type(record['page']) is not type(self.pages[key]['page']):
            raise ValueError('Use the same page identity type as the registered source page; do not mix 1 and "1".')
        box=record['bbox_original']
        if not isinstance(box,list) or len(box)!=4 or any(type(x) is not int for x in box):
            raise ValueError('Crop needs integer original-pixel bounds.')
        page=self.pages[key];width,height=page['dimensions']
        if not (0<=box[0]<box[2]<=width and 0<=box[1]<box[3]<=height):
            raise ValueError('Crop lies outside its registered source page.')
        pixels=self.images[key].crop(box)
        supplied=record.get('image')
        if supplied is not None:
            path=self.base/supplied
            if not path.is_file():raise ValueError('Missing supplied crop: '+str(path))
            with Image.open(path) as image:
                if image.size!=pixels.size:raise ValueError('Crop dimensions differ from bbox_original.')
                if image.convert('RGBA').tobytes()!=pixels.tobytes():
                    raise ValueError('Supplied crop pixels do not match the stated page and coordinates. Derive from the registered page instead; do not recompress crops.')
        crop_key=key+(tuple(box),)
        if crop_key not in self.crops:
            dest=Path('crops')/('crop-'+str(len(self.crops)+1).zfill(4)+'.png')
            # Retain source RGB when opaque; display transparency is handled separately.
            if pixels.getextrema()[3]==(255,255):pixels=pixels.convert('RGB')
            pixels.save(self.stage/dest)
            self.crops[crop_key]=dest.as_posix()
        result=dict(record,image=self.crops[crop_key],source_page_sha256=page['sha256'],
                    crop_verification='derived_from_pinned_page',supplied_crop_verified=supplied is not None)
        return result


    def pad(self, record, fraction):
        """Re-crop a verified box with a margin taken from the pinned page, clamped to its edges."""
        box=record['bbox_original'];width,height=self.pages[page_key(record['source_id'],record['page'])]['dimensions']
        pixels=round(fraction*(box[3]-box[1]))
        wanted=[box[0]-pixels,box[1]-pixels,box[2]+pixels,box[3]+pixels]
        padded=[max(0,wanted[0]),max(0,wanted[1]),min(width,wanted[2]),min(height,wanted[3])]
        result=self.crop(dict(record,bbox_original=padded,image=None))
        result['display_margin']={'fraction':fraction,'pixels':pixels,'requested_bbox_original':box,
                                  'padded_bbox_original':padded,'clamped_to_page':padded!=wanted}
        return result


def coalesce_samples(records, sources):
    """Merge near-identical same-page coverage, retaining each sample's exact locator."""
    groups=[]
    for record in records:
        alias={k:record[k] for k in ('source_id','page','sample_id','bbox_original')}
        x=record['bbox_original'];area=(x[2]-x[0])*(x[3]-x[1])
        for group in groups:
            if page_key(group['source_id'],group['page'])!=page_key(record['source_id'],record['page']):continue
            y=group['bbox_original'];other=(y[2]-y[0])*(y[3]-y[1])
            intersection=max(0,min(x[2],y[2])-max(x[0],y[0]))*max(0,min(x[3],y[3])-max(x[1],y[1]))
            union=[min(x[0],y[0]),min(x[1],y[1]),max(x[2],y[2]),max(x[3],y[3])]
            if intersection/min(area,other)>=0.85 and (union[2]-union[0])*(union[3]-union[1])<=1.25*max(area,other):
                aliases=group['aliases']+[alias]
                combined={k:group[k] for k in ('source_id','page','sample_id','role')}
                combined['bbox_original']=union
                group.clear();group.update(sources.crop(combined),aliases=aliases)
                break
        else:groups.append(dict(record,aliases=[alias]))
    return groups
