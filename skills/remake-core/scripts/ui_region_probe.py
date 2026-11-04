"""Measure expected foreground extent or ink intrusion in a registered local UI slot."""
from PIL import ImageChops

def measure(image, bounds, probes):
    if not isinstance(probes,list) or not probes:
        raise ValueError('pixel_regions needs nonempty rules')
    x,y,w,h=bounds
    results=[]
    for rule in probes:
        if not isinstance(rule,dict) or not isinstance(rule.get('id'),str) or not rule['id']:
            raise ValueError('named region required')
        left,top,right,bottom=rule['region']
        if not (0<=left<right<=1 and 0<=top<bottom<=1):raise ValueError('invalid slot-relative region')
        box=(round(x+left*w),round(y+top*h),round(x+right*w),round(y+bottom*h))
        if not (0<=box[0]<box[2]<=image.width and 0<=box[1]<box[3]<=image.height):raise ValueError('region offscreen/empty')
        im=image.crop(box).convert('RGB')
        bands=im.split()
        masks=[]
        if len(rule['rgb_min']) != 3 or len(rule['rgb_max']) != 3: raise ValueError('three RGB channels required')
        for band,lo,hi in zip(bands,rule['rgb_min'],rule['rgb_max']):
            if not (type(lo) is int and type(hi) is int and 0<=lo<=hi<=255):raise ValueError('invalid calibrated RGB range')
            masks.append(band.point([255 if lo<=i<=hi else 0 for i in range(256)]))
        mask=ImageChops.darker(ImageChops.darker(masks[0],masks[1]),masks[2])
        if rule.get('invert',False):mask=ImageChops.invert(mask)
        b=mask.getbbox(); width=(b[2]-b[0]) if b else 0;height=(b[3]-b[1]) if b else 0
        values=dict(fill=mask.histogram()[255]/(im.width*im.height),width=width/im.width,height=height/im.height)
        metric=rule['metric']; value=values[metric];low,high=rule['range']
        if not (0<=low<=high<=1):raise ValueError('invalid allowed range')
        results.append(dict(id=rule['id'],metric=metric,box=box,value=round(value,5),expected=[low,high],passed=low<=value<=high))
    return results
