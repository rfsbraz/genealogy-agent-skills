#!/usr/bin/env python3
"""Create faithful, traceable manuscript display views. No recognition or reconstruction."""
import hashlib
import math
from pathlib import Path
import shutil


def image_info(path):
    try:
        from PIL import Image
    except ImportError as exc:
        raise ValueError('Packet image preparation requires Pillow. Supply that dependency before building packets.') from exc
    with Image.open(path) as image:
        if getattr(image, 'n_frames', 1) != 1:
            raise ValueError('Render each physical page to a separate image first.')
        if image.getexif().get(274, 1) != 1:
            raise ValueError('Apply and record EXIF orientation before assigning original-pixel coordinates.')
        image.load()
        return image.size


def validate_record(record, base):
    for key in ('source_id', 'sample_id', 'image'):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError('Each image needs a nonempty ' + key)
    page = record.get('page')
    if isinstance(page, bool) or not ((isinstance(page, int) and page > 0) or (isinstance(page, str) and page.strip())):
        raise ValueError('Each image needs its own physical page identity.')
    box = record.get('bbox_original')
    if not isinstance(box, list) or len(box) != 4 or any(type(x) is not int for x in box) or not (0 <= box[0] < box[2] and 0 <= box[1] < box[3]):
        raise ValueError('Each image needs integer original-pixel crop bounds.')
    path = Path(base) / record['image']
    if not path.is_file():
        raise ValueError('Missing source image: ' + str(path))
    width, height = image_info(path)
    if (width, height) != (box[2] - box[0], box[3] - box[1]):
        raise ValueError('Crop dimensions differ from bbox_original; supply an unscaled crop and record earlier transforms separately.')
    return width, height


def intervals(length, tile=1600, overlap=160):
    if length<=tile:return [(0,length)]
    count=math.ceil((length-overlap)/(tile-overlap))
    width=math.ceil((length+overlap*(count-1))/count)
    return [(i*(width-overlap),min(i*(width-overlap)+width,length)) for i in range(count)]


def make_views(record, base, folder, asset_id, contrast=False):
    """Copy verified crop bytes and emit neutral, balanced display tiles with exact lineage."""
    if contrast:raise ValueError('Contrast views are disabled in reading packets; compression blocks can mimic strokes.')
    from PIL import Image, __version__ as pillow_version
    path, folder = Path(base) / record['image'], Path(folder)
    width, height = validate_record(record, base)
    original_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    filename = asset_id + '-original' + path.suffix.lower()
    shutil.copyfile(path, folder / filename)
    identity = {k: record[k] for k in ('source_id', 'page', 'sample_id', 'bbox_original')}
    result = dict(identity, source_page_sha256=record.get('source_page_sha256'), crop_verification=record.get('crop_verification'), aliases=record.get('aliases',[]), asset_id=asset_id, role=record['role'], original_file=filename,
                  original_sha256=original_hash, original_dimensions=[width, height], views=[])
    original = dict(view_id=asset_id+'-original', file=filename, kind='original',
                    dimensions=[width, height], sha256=original_hash,
                    source_box_in_crop=[0, 0, width, height], source_bbox_original=record['bbox_original'],
                    transform={'operation':'byte_copy', 'scale':[1,1]})
    margin=record.get('display_margin')
    if margin:original['transform']['margin']=margin
    result['views'].append(original)
    with Image.open(path) as source:
        source.load()
        rgba=source.convert('RGBA')
        display=Image.alpha_composite(Image.new('RGBA',source.size,'white'),rgba).convert('RGB')
        if record['role'] == 'context':
            # Whole page is orientation only. D receives separate line and target details.
            scale = min(1, 1400/max(width,height))
            size = (max(1,round(width*scale)),max(1,round(height*scale)))
            variants = [('overview',display.resize(size,Image.Resampling.LANCZOS),
                         {'resampling':'LANCZOS','orientation_only':True})]
            overlap = 160
        else:
            scale = min(8,max(1,math.ceil(max(1200/width,160/height))))
            size = (width*scale,height*scale)
            enlarged=display.resize(size,Image.Resampling.NEAREST)
            # Overlap tiles by at least one enlarged text line, estimated as the crop height up to 200 source pixels.
            overlap = min(800, max(160, scale*min(height,200)))
            parameters = {'resampling':'NEAREST','contrast':'none','tile_overlap':overlap}
            if margin:parameters['margin']=margin
            variants=[('enlarged',enlarged,parameters)]
        for kind, view, parameters in variants:
            xs, ys = intervals(view.width, overlap=overlap), intervals(view.height, overlap=overlap)
            if len(xs)*len(ys)>48:
                raise ValueError('Too many display tiles; prepare smaller source regions before dispatch.')
            for y,y_end in ys:
                for x,x_end in xs:
                    bounds=[x,y,x_end,y_end]
                    piece=view.crop(bounds)
                    view_id=asset_id+'-'+kind+'-'+str(len(result['views'])).zfill(3)
                    name=view_id+'.png'; piece.save(folder/name)
                    sx,sy=view.width/width,view.height/height
                    box=[bounds[0]/sx,bounds[1]/sy,bounds[2]/sx,bounds[3]/sy]
                    origin=record['bbox_original']
                    mapped=[box[0]+origin[0],box[1]+origin[1],box[2]+origin[0],box[3]+origin[1]]
                    result['views'].append({'view_id':view_id,'file':name,'kind':kind,
                        'dimensions':list(piece.size),'sha256':hashlib.sha256((folder/name).read_bytes()).hexdigest(),
                        'source_box_in_crop':box,'source_bbox_original':mapped,
                        'transform':dict(parameters,operation='resize_then_tile',scale=[sx,sy],
                                         tile_box_in_resized=bounds,display_background='#ffffff',tool='Pillow',version=pillow_version)})
    result['limitations']=['Enlargement adds no source detail. Compare neutral enlarged views with the original. JPEG blocks are not evidence of pen strokes.']
    if min(width,height)<16:
        result['limitations'].append('Very small source dimension; inspect legibility before dispatch.')
    return result


def mark_location(asset, target, anchor, folder, index):
    """Separate orientation copy; the coloured outlines are never text evidence."""
    from PIL import Image, ImageDraw
    folder=Path(folder)
    with Image.open(folder/asset['original_file']) as original:
        image=Image.alpha_composite(Image.new('RGBA',original.size,'white'),original.convert('RGBA')).convert('RGB')
    origin=asset['bbox_original'];draw=ImageDraw.Draw(image)
    def relative(box):return [box[0]-origin[0],box[1]-origin[1],box[2]-origin[0],box[3]-origin[1]]
    for box,color in ((target,'red'),(anchor,'blue')):
        if box is not None:
            x0,y0,x1,y1=relative(box)
            draw.rectangle([max(0,x0-2),max(0,y0-2),min(image.width-1,x1+1),min(image.height-1,y1+1)],outline=color,width=2)
    view_id='location-'+str(index).zfill(3);filename=view_id+'.png';image.save(folder/filename)
    view={'view_id':view_id,'file':filename,'kind':'locator','dimensions':list(image.size),
        'sha256':hashlib.sha256((folder/filename).read_bytes()).hexdigest(),
        'source_bbox_original':origin,'target_bbox_in_line':relative(target),
        'anchor_bbox_in_line':relative(anchor) if anchor else None,
        'transform':{'operation':'orientation_overlay','scale':[1,1],
                     'target_outline':'red','anchor_outline':'blue','letter_evidence':False}}
    asset['views'].append(view)
    return view
