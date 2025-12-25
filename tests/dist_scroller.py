#!/usr/bin/python3
import sys,os,argparse,math
import png

##########################################################################
##########################################################################

def create_rgba_image(w,h):
    image=[]
    for y in range(h): image.append(w*[255,0,255,255])
    return image

def resize_rgba_image(image):
    image2=[]
    for y in range(len(image)):
        image2_row=[]
        for x in range(0,len(image[y]),4):
            image2_row+=4*image[y][x:x+4]
        image2.append(image2_row)
    return image2

def get_rgba_image_size(image): return (len(image[0])//4,len(image))

def get_rgba_indexes(image,x,y):
    y=int(y)
    if y<0 or y>=len(image): return (None,None)
    x=int(x)*4
    if x<0 or x>=len(image[y]): return (None,None)
    return (y,x)

def get_rgba_pixel(image,x,y):
    i,j=get_rgba_indexes(image,x,y)
    if i is None: return (0,0,0,255)
    return (image[i][j+0],image[i][j+1],image[i][j+2],image[i][j+3])

def put_rgba_pixel(image,x,y,rgba):
    i,j=get_rgba_indexes(image,x,y)
    if i is None: return
    image[i][j+0]=rgba[0]
    image[i][j+1]=rgba[1]
    image[i][j+2]=rgba[2]
    image[i][j+3]=rgba[3]

# def plot_rgba_pixel(image,x,y,r,g,b,a):
#     x=int(x)*4
#     y=int(y)

#     if y<0: return
#     if y>=len(image): return
#     if x<0: return
#     if x>=len(image[y]): return

#     image[y][x+0]=r
#     image[y][x+1]=g
#     image[y][x+2]=b
#     image[y][x+3]=a

# def copy_rgba_pixel(dest,dx,dy,src,sx,sy):
#     dx=int(dx)*4
#     dy=int(dy)
#     sx=int(sx)*4
#     sy=int(sy)
    
#     if dy<0: return
#     if dy>=len(dest): return
#     if dx<0: return
#     if dx>=len(dest[dy]): return
#     if sy<0: return
#     if sy>=len(src): return
#     if sx<0: return
#     if sx>=len(src[sy]): return
    
#     assert dy>=0 and dy<len(dest)
#     assert sy>=0 and sy<len(src),(sy,len(src))
#     assert dx>=0 and dx+3<len(dest[dy]),(dx,len(dest[dy]))
#     assert sx>=0 and sx+3<len(src[sy])#,(sx,sy,len(src[0]),len(src))
#     sa=src[sy][sx+3]
#     assert sa>=0 and sa<256
#     sa/=255
#     def blend(s,d):
#         assert s>=0 and s<256
#         s/=255
#         assert d>=0 and d<256
#         d/=255
#         v=int((s*sa+d*(1-sa))*255.)
#         assert v>=0 and v<256
#         return v
              
#     dest[dy][dx+0]=blend(src[sy][sx+0],dest[sy][sx+0])
#     dest[dy][dx+1]=blend(src[sy][sx+1],dest[sy][sx+1])
#     dest[dy][dx+2]=blend(src[sy][sx+2],dest[sy][sx+2])
#     dest[dy][dx+3]=src[sy][sx+3]

def main2(options):
    png_result=png.Reader(filename='geebeeyay_8x16.png').asRGBA()
    print('font: %dx%d'%(png_result[0],png_result[1]))

    image=[]
    for row in png_result[2]: image.append(row)

    print(len(image),len(image[0]))

    glyphs=[]
    x=0
    glyph_width=8
    glyph_height=16
    assert png_result[1]==glyph_height
    while x<png_result[0]:
        glyph=[]
        for y in range(png_result[1]):
            glyph.append(image[y][x*4:(x+glyph_width)*4])
        glyphs.append(glyph)
        x+=glyph_width

        # if options.output_folder is not None:
        #     png.from_array(glyph,'RGBA').save(os.path.join(options.output_folder,'dist_scroller.glyph.%d.png'%

    text='DISTORTION'#SCROLL TEXT TEST'

    screen_width=80
    num_frames=250
    num_x_cycle_frames=301
    num_y_cycle_frames=201
    x_scale=8
    y_scale=8
    half_res_x_scale=False

    for frame_idx in range(num_frames):
        image=create_rgba_image(screen_width,172)

        for x in range(screen_width):
            theta=(frame_idx*2+(x&~1))%num_y_cycle_frames/num_y_cycle_frames*2*math.pi
            y_offset=math.sin(theta)*16

            # halve Y wobble resolution
            neg=y_offset<0
            y_offset=abs(y_offset)#//2*2
            if neg: y_offset=-y_offset
            #plot_rgba_pixel(image,x,y,255,255,255,255)

            # print('x=%d y_offset=%d'%(x,y_offset))

            index=(x//8)%len(text)
            ch=ord(text[index])
            assert ch>=32 and ch<=127
            ch-=32
            assert ch<len(glyphs)

            for y in range(len(image)):
                theta=(frame_idx*10+(y&~1))%num_x_cycle_frames/num_x_cycle_frames*2*math.pi
                # half res X movement :(
                dx=int(math.sin(theta)*x_scale)
                if half_res_x_scale:
                    dx//=2
                    dx*=2
                
                sy=y%glyph_height-y_offset
                if sy<0: sy+=glyph_height
                elif sy>=glyph_height: sy-=glyph_height

                p=get_rgba_pixel(glyphs[ch],x%glyph_width,sy)
                put_rgba_pixel(image,x+dx,y,p)
                # copy_rgba_pixel(image,x+dx,y,
                #                 glyphs[ch],x%glyph_width,sy)
            
        print('frame %d: %s'%(frame_idx,get_rgba_image_size(image)))

        if options.output_folder is not None:
            image=resize_rgba_image(image)

            output_path=os.path.join(options.output_folder,
                                     'dist_scroller.%d.png'%frame_idx)
            png.from_array(image,'RGBA').save(output_path)
            # with open(output_path,'wb') as f:
            #     png.Writer(len(image[0])//4,len(image),alpha=True).write(f,image)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('-o',dest='output_folder',metavar='FOLDER',help='''where to write output files''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
