#!/usr/bin/python3
import sys,os,argparse,math,subprocess
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

def lerp(a,b,t): return a+t*(b-a)
    
def blend_rgba_pixel(image,x,y,rgba):
    dest=get_rgba_pixel(image,x,y)
    a=rgba[3]
    assert a>=0 and a<256
    a/=255
    rgba2=(int(lerp(dest[0],rgba[0],a)),
           int(lerp(dest[1],rgba[1],a)),
           int(lerp(dest[2],rgba[2],a)),
           rgba[3])
    put_rgba_pixel(image,x,y,rgba2)

def copy_rgba_block(destimage,destx,desty,srcimage,srcx,srcy,srcw,srch):
    for dy in range(srch):
        for dx in range(srcw):
            pixel=get_rgba_pixel(srcimage,srcx+dx,srcy+dy)
            put_rgba_pixel(destimage,destx+dx,desty+dy,pixel)

def get_linear_value(x):
    assert x>=0 and x<256
    return math.pow(x/255,2.2)
    
def get_linear_rgb(rgba):
    return (get_linear_value(rgba[0]),
            get_linear_value(rgba[1]),
            get_linear_value(rgba[2]))

def make_linear_mapping(mapping):
    for i in range(len(mapping)):
        assert mapping[i][1]>=0 and mapping[i][1]<8
        mapping[i]=(get_linear_rgb(mapping[i][0]),mapping[i][1])
    
default_mapping=[]
for i in range(8):
    default_mapping.append(((255 if (i&1)!=0 else 0,
                            255 if (i&2)!=0 else 0,
                            255 if (i&4)!=0 else 0),
                            i))
make_linear_mapping(default_mapping)

print(default_mapping)

# should have loaded it in as a palettized image directly... oh well
geebeeyay_8x16_mapping=[
    ((0x00,0x00,0x60),4),
    ((0xb7,0xff,0x5f),1),
    ((0x67,0xb7,0x33),3),
    ((0x23,0x53,0x00),7),
    ((0x00,0x00,0x00),0),
]
make_linear_mapping(geebeeyay_8x16_mapping)

def get_bbc_rgba(pixel,mapping=default_mapping):
    gpixel=get_linear_rgb(pixel)

    closest=None
    closest_dist2=None

    for rgb,bbc_index in mapping:
        dr=rgb[0]-gpixel[0]
        dg=rgb[1]-gpixel[1]
        db=rgb[2]-gpixel[2]

        dist2=dr*dr+dg*dg+db*db
        if closest is None or dist2<closest_dist2:
            closest=bbc_index
            closest_dist2=dist2

    return (255 if (closest&1)!=0 else 0,
            255 if (closest&2)!=0 else 0,
            255 if (closest&4)!=0 else 0,
            255)

def main2(options):
    png_result=png.Reader(filename='geebeeyay_8x16.png').asRGBA()
    print('font: %dx%d'%(png_result[0],png_result[1]))

    image=[]
    for row in png_result[2]: image.append(row)

    glyphs=[]
    x=0
    glyph_width=8
    glyph_height=16
    assert png_result[1]==glyph_height
    while x<png_result[0]:
        glyph=create_rgba_image(glyph_width,glyph_height)
        for y in range(png_result[1]):
            for dx in range(glyph_width):
                pixel=get_rgba_pixel(image,x+dx,y)
                pixel=get_bbc_rgba(pixel,geebeeyay_8x16_mapping)
                put_rgba_pixel(glyph,dx,y,pixel)
            #glyph.append(image[y][x*4:(x+glyph_width)*4])
        glyphs.append(glyph)
        x+=glyph_width

        # if options.output_folder is not None:
        #     png.from_array(glyph,'RGBA').save(os.path.join(options.output_folder,'dist_scroller.glyph.%d.png'%

    text='DISTORTION SCROLLER TEST! '

    screen_width=80

    # Assume BBC resolution is 320x256. (Scale down/up for 80/160/640
    # modes.) So 16:9 would be 320x(320/16*9)=320x180. Or 320x176 (22*8),
    # rounded down to a character row.
    # 
    # Actual pixel aspect ratio is 24:25, or 0.96:1. So 16:9 would
    # actually be more like 320x(320*24/25/16*9)=320x173. 320x168
    # (21*8) would be even better. More blank rows!
    
    screen_height=168
    num_frames=250
    num_x_cycle_frames=300
    num_y_cycle_frames=110

    # every 2 pixels means 2 extra columns per row.
    x_scale=8
    assert x_scale%2==0

    # if more than half the glyph height, it just wraps around - but
    # the screen is made up from repeating the same rows, so it
    # visually looks correct.
    y_scale=16

    # half res X scale looks a bit crap... will probably just have to
    # suck it up and attempt to do the full res.
    half_res_x_scale=False

    # don't think half res Y scale is actually going to be relevant,
    # but it doesn't look too objectionable.
    half_res_y_scale=False

    # X wobble vertical resolution, since address can only change at
    # start of row.
    #
    # 8 looks fine and can be dealt with using timer IRQs.
    #
    # 4 looks usefully better, if the extra overhead (time/memory...)
    # doesn't prove too much.
    char_row_height=4

    # gap between chars, if any.
    #
    # (Annoyingly, it looks a lot better with gap=0, which is a shame
    # as it means that the last column of each shifted char will have
    # to be merged at some point with the first column of the next
    # one.)
    gap=0

    scroller_x=0

    def get_int_maybe_half_res(n,halve):
        if halve:
            # round to zero
            if n>=0: n//=2
            else: n=-(-n//2)
            n*=2
        return int(n)

    def create_frame_image_3(frame_idx):
        assert glyph_height%char_row_height==0
        assert screen_height%char_row_height==0
        
        logical_width=screen_width+x_scale*2

        # render by repeatedly copying a single row that's 1 glyph
        # high
        image=create_rgba_image(logical_width,glyph_height)

        text_base_x=-screen_width+frame_idx

        if frame_idx==0:
            print('logical_width=%d'%logical_width)

        for y in range(glyph_height):
            for x in range(logical_width):
                y_theta=(frame_idx*2+(get_int_maybe_half_res(x,True)))%num_y_cycle_frames/num_y_cycle_frames*2*math.pi
                y_offset=math.sin(y_theta)*y_scale
                y_offset=get_int_maybe_half_res(y_offset,half_res_y_scale)
                
                text_x=text_base_x+x
                if text_x<0: ch=32
                else: ch=ord(text[text_x//(glyph_width+gap)%len(text)])
                    
                assert ch>=32 and ch<127
                ch-=32
                assert ch<len(glyphs)

                glyph_x=text_x%(glyph_width+gap)
                if glyph_x>=glyph_width:
                    # read gap columns from the space char
                    ch=0
                    glyph_x=0

                pixel=get_rgba_pixel(glyphs[ch],
                                     glyph_x,
                                     (y+y_offset)%glyph_height)
                put_rgba_pixel(image,x,y,pixel)
            #blend_rgba_pixel(image,79,y,(255,255,255,128))

        full_image=create_rgba_image(screen_width,screen_height)
        num_rows=screen_height//char_row_height
        for row in range(num_rows):
            dest_y=row*char_row_height
            x_theta=(frame_idx*2+row)%num_x_cycle_frames/num_x_cycle_frames*2*math.pi
            x_offset=math.sin(x_theta)*x_scale

            src_x=x_scale+x_offset
            src_y=dest_y%glyph_height

            copy_rgba_block(full_image,0,dest_y,
                            image,src_x,src_y,screen_width,char_row_height)

            # for x in range(screen_width):
            #     blend_rgba_pixel(full_image,x,dest_y,(255,255,255,128))

        # full_image=create_rgba_image(screen_width,screen_height)
        # for y in range(0,screen_height,glyph_height):
        #     copy_rgba_block(full_image,0,y,
        #                     image,0,0,screen_width,glyph_height)
        #     if y>0:
        #         for x in range(screen_width):
        #             put_rgba_pixel(full_image,x,y,(255,255,255,128))

        return {'':full_image,'.one_row':image}

    def create_frame_image_2(frame_idx):
        # render starting from screen (x,y)
        image=create_rgba_image(screen_width,screen_height)

        text_base_x=-screen_width+frame_idx
        
        for y in range(screen_height):
            for x in range(screen_width):
                x_theta=(frame_idx*2+(y//char_row_height*char_row_height))%num_x_cycle_frames/num_x_cycle_frames*2*math.pi
                x_offset=math.sin(x_theta)*x_scale
                x_offset=get_int_maybe_half_res(x_offset,half_res_x_scale)

                # TODO: is it going to be feasible to have full res X?
                y_theta=(frame_idx*2+(get_int_maybe_half_res(x,True)))%num_y_cycle_frames/num_y_cycle_frames*2*math.pi
                y_offset=math.sin(y_theta)*y_scale
                y_offset=get_int_maybe_half_res(y_offset,half_res_y_scale)

                text_x=text_base_x+x+x_offset
                if text_x<0: ch=32
                else: ch=ord(text[text_x//glyph_width%len(text)])
                    
                assert ch>=32 and ch<127
                ch-=32
                assert ch<len(glyphs)

                pixel=get_rgba_pixel(glyphs[ch],
                                     text_x%glyph_width,
                                     (y+y_offset)%glyph_height)
                put_rgba_pixel(image,x,y,pixel)

                # if x%2==0 or y%char_row_height==0:
                #     blend_rgba_pixel(image,x,y,(255,255,255,64))

        return {'':image}
    
    def create_frame_image_1(frame_idx):
        # render forward
        image=create_rgba_image(screen_width,screen_height)

        for x in range(screen_width):
            theta=(frame_idx*2+(x&~1))%num_y_cycle_frames/num_y_cycle_frames*2*math.pi
            y_offset=math.sin(theta)*y_scale

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
        return {'':image}

    names=set()
    full_progress='*'*50
    for frame_idx in range(num_frames):
        images=create_frame_image_3(frame_idx)

        sys.stdout.write('\r[%-*.*s]'%(len(full_progress),int(frame_idx/(num_frames-1)*len(full_progress)),full_progress))

        if options.intermediate_folder is not None:
            for name,image in images.items():
                names.add(name)
                image=resize_rgba_image(image)

                output_path=os.path.join(options.intermediate_folder,
                                         'dist_scroller%s.%d.png'%(name,frame_idx))
                png.from_array(image,'RGBA').save(output_path)

    print()

    if (options.intermediate_folder is not None and
        options.output_folder is not None):
        for name in names:
            argv=['ffmpeg',
                  '-y',
                  '-r','50',
                  '-i',os.path.join(options.intermediate_folder,
                                    'dist_scroller%s.%%d.png'%name),
                  '-pix_fmt','yuv420p',
                  os.path.join(options.output_folder,
                               'dist_scroller%s.mp4'%name)]
            subprocess.run(argv,check=True)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('--intermediate',dest='intermediate_folder',metavar='FOLDER',help='''where to write intermediate files''')
    parser.add_argument('--output',dest='output_folder',metavar='FOLDER',help='''where to write output files''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
