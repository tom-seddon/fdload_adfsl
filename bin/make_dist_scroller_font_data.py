#!/usr/bin/python3
import sys,os,os.path,argparse,json,collections,contextlib
import png

##########################################################################
##########################################################################

V2=collections.namedtuple('V2','x y')

##########################################################################
##########################################################################

g_verbose=False

def pv(msg):
    if g_verbose:
        sys.stdout.write(msg)
        sys.stdout.flush()

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

def ffatal(path,msg,row=None,column=None):
    sys.stderr.write('%s%s%s: FATAL: %s'%
                     (path,
                      '' if row is None else ':%s'%row,
                      '' if column is None else ':%s'%column,
                      msg))
    sys.exit(1)

##########################################################################
##########################################################################

def encode_mode2(left,right):
    def encode(a):
        assert a>=0 and a<16
        r=0
        if a&8: r|=1<<7
        if a&4: r|=1<<5
        if a&2: r|=1<<3
        if a&1: r|=1<<1
        return r
    return encode(left)|encode(right)>>1

##########################################################################
##########################################################################

def get_bbc_colour(index):
    assert index>=0 and index<8
    return ((255 if index&1 else 0),
            (255 if index&2 else 0),
            (255 if index&4 else 0))

##########################################################################
##########################################################################

def get_char_description(c):
    r='%d (0x%x)'%(c,c)
    if c>=32 and c<127: r+=" ('%c')"%chr(c)
    return r

##########################################################################
##########################################################################

#Glyph=collections.namedtuple('Glyph','pos size')
Font=collections.namedtuple('Font','image glyph_size glyphs_map')

Char=collections.namedtuple('Char','index')


def load_font(png_path,glyph_size,first_glyph):
    assert glyph_size.x%2==0

    png_result=png.Reader(filename=png_path).read()
    png_size=V2(png_result[0],png_result[1])
    png_data=png_result[2]
    png_info=png_result[3]

    if 'palette' not in png_info: fatal('%s: not palettized'%png_path)

    glyphs_map={}
    if first_glyph is not None:
        if png_size.x%glyph_size.x!=0:
            ffatal(png_path,
                   'image width (%d) not multiple of glyph width (%d)'%
                   (png_size.x,glyph_size.x))

        if png_size.y%glyph_size.y!=0:
            ffatal(png_path,
                   'image height (%d) not multiple of glyph height (%d)'%
                   (png_size.y,glyph_size.y))

        glyph=first_glyph
        for y in range(0,png_size.y,glyph_size.y):
            for x in range(0,png_size.x,glyph_size.x):
                assert glyph not in glyphs_map
                glyphs_map[glyph]=V2(x,y)
                glyph+=1
                
    return Font(image=[row for row in png_data],
                glyph_size=glyph_size,
                glyphs_map=glyphs_map)

##########################################################################
##########################################################################

@contextlib.contextmanager
def output_text_file(path):
    if path=='-': yield sys.stdout
    else:
        with open(path,'wt') as f: yield f

##########################################################################
##########################################################################

def main2(options):
    global g_verbose;g_verbose=options.verbose

    scroll_data=['DISTORTION SCROLLER PROTOTYPE']

    png_path=os.path.join(options.root_path,'tests/geebeeyay_8x16.png')
    font=load_font(png_path,
                   glyph_size=V2(8,16),
                   first_glyph=32)

    bbc_from_png={0:4,
                  1:1,
                  2:3,
                  3:7,
                  4:0}
    png_background=0
    for y in range(len(font.image)):
        for x in range(len(font.image[y])):
            index=font.image[y][x]
            if index not in bbc_from_png:
                fatal('%s: unexpected palette index at (%d,%d): %d'%
                      (png_path,x,y,index))

    # find all used chars, and check all are available in font.
    # also note all char pairs.
    glyph_index_by_char={}
    # last_char=None
    for part in scroll_data:
        if isinstance(part,str):
            for char in part:
                char=ord(char)
                if char not in font.glyphs_map:
                    fatal('char not in font: %s'%get_char_description(char))
                if char not in glyph_index_by_char:
                    glyph_index_by_char[char]=len(glyph_index_by_char)

                # if last_char is not None:
                #     used_char_pairs.add((last_char,char))

                # last_char=char

    pv('Used chars: %s\n'%('; '.join([get_char_description(c) for c in glyph_index_by_char.keys()])))
    # pv('Used char pairs: %s\n'%list(used_char_pairs))
    
    if options.output_glyph_s65 is not None:
        with output_text_file(options.output_glyph_s65) as f:
            f.write('; automatically generated output-glyph-s65 output. do not edit.\n')
            f.write('\n\n')
            for char,index in glyph_index_by_char.items():
                pos=font.glyphs_map[char]
                
                def get_column_name(column):
                    return 'X' if column is None else str(column)

                def write_column(left_column,right_column):
                    f.write('    ; %s+%s\n'%(get_column_name(left_column),
                                             get_column_name(right_column)))

                    bytes=[]
                    for y in range(font.glyph_size.y):
                        def get_bbc(x):
                            if x is None: return 0
                            else:
                                value=font.image[pos.y+y][pos.x+x]
                                value=bbc_from_png[value]
                                return value

                        bytes.append(encode_mode2(get_bbc(left_column),
                                                  get_bbc(right_column)))
                    
                    # TODO: actually, the 16th byte of the 2nd copy
                    # will never be used... and it can probably be
                    # eliminated? Offsets into this table will be
                    # generated sequentially.
                    for i in range(2):
                        f.write('    .byte %s\n'%
                                (','.join(['$%02x'%byte for byte in bytes])))

                f.write('char%02x: .block\n'%index)
                
                write_column(None,0)
                write_column(0,1)
                write_column(1,2)
                write_column(2,3)
                write_column(3,4)
                write_column(4,5)
                write_column(5,6)
                write_column(6,7)
                write_column(7,None)
                            
                f.write('    .endblock\n')

            if 32 in glyph_index_by_char:
                f.write('char_blank_column=char%02x+32\n'%glyph_index_by_char[32])

    if options.output_text_s65 is not None:
        with output_text_file(options.output_text_s65) as f:
            f.write('; automatically generated output-text-s65 output. do not edit.\n\n')
            f.write('scroll_text:\n')
            for part in scroll_data:
                if isinstance(part,str):
                    for char in part:
                        char=ord(char)
                        index=glyph_index_by_char[char]
                        f.write('    .word char%02x ; %s\n'%
                                (index,
                                 get_char_description(char)))
                else: assert False,type(part)
            f.write('    .word 0\n')

##########################################################################
##########################################################################

def main(argv):
    def auto_int(x): return int(x,0)
    
    p=argparse.ArgumentParser()
    p.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')
    p.add_argument('--root',metavar='FOLDER',dest='root_path',default='.',help='''treat %(metavar)s as root of project. Default: %(default)s''')
    p.add_argument('--output-glyph-s65',metavar='FILE',help='''write glyph data source code to %(metavar)s (specify - for stdout)''')
    p.add_argument('--output-text-s65',metavar='FILE',help='''write scroll text data to %(metavar)s (specify - for stdout)''')

    main2(p.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
