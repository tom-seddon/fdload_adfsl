import collections
import png

##########################################################################
##########################################################################

V2=collections.namedtuple('V2','x y')

##########################################################################
##########################################################################

def check_pixel(pixel):
    assert isinstance(pixel,list) or isinstance(pixel,tuple)
    assert len(pixel)==4

##########################################################################
##########################################################################

class RGBAImage:
    def __init__(self,size,data):
        self._size=size
        self._data=data

    @property
    def size(self): return self._size

    def get_rgba(self,x,y,default=(0,0,0,255)):
        y=int(y)
        if y<0 or y>=self._size.y: return default
        x=int(x)
        if x<0 or x>=self._size.x: return default
        x*=4
        return self._data[y][x:x+4]

    def put_rgba(self,x,y,pixel):
        y=int(y)
        if y<0 or y>=self.size.y: return
        x=int(x)
        if x<0 or x>=self._size.x: return default
        x*=4
        assert len(pixel)==4
        self._data[y][x:x+4]=pixel

    def save_png(self,path):
        png.from_array(self._data,'RGBA').save(path)

##########################################################################
##########################################################################

def create_rgba(size,pixel=(255,0,255,255)):
    check_pixel(pixel)
    data=[]
    row=size.x*[int(pixel[0]),int(pixel[1]),int(pixel[2]),int(pixel[3])]
    for y in range(size.y): data.append(row[:])
    return RGBAImage(size,data)

##########################################################################
##########################################################################

