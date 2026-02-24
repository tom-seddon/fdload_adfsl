#!/usr/bin/python3
import sys,os,argparse,math,subprocess
import png
import zimg
from zimg import V2

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
    sys.stderr.write('\nFATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def main2(options):
    global g_verbose;g_verbose=options.verbose

    prototype_name='cylinder_text'

    screen_size=V2(160,168)

    square_size=V2(8,16)

    white=(255,255,255,255)
    black=(0,0,0,255)

    # 168/6=28
    pattern=[
        'TTTTT',
        '  T  ',
        '  T  ',
        '  T  ',
        '  T  ',
        '  T  ',
        '     ',
        'EEEEE',
        'E    ',
        'EEE  ',
        'E    ',
        'EEEEE',
        '     ',
        ' SSSS',
        'S    ',
        ' SSS ',
        '    S',
        'SSSS ',
        '     ',
        'TTTTT',
        '  T  ',
        '  T  ',
        '  T  ',
        '  T  ',
        '  T  ',
    ]

    num_steps=125
    # for i in range(num_steps):
    #     theta=i/num_steps*2*math.pi
    #     s=math.sin(theta)
    #     c=math.cos(theta)
    #     x=int(10+s*9.999)
    #     print('i=%d: theta=%.3f: s=%.3f c=%.3f x=%d'%(i,theta,s,c,x))
    
    def create_frame_1(frame_index):
        image=zimg.create_rgba(screen_size)

        theta=(frame_index/num_steps)*2*math.pi
        bar_x=int(screen_size.x//2+math.sin(theta)*screen_size.x//2-0.00001)

        for screen_y in range(screen_size.y):
            bg=(0,0,255,255)
            fg=(255,255,255,255)
            pattern_row=None
            pattern_index=screen_y//6
            if pattern_index<len(pattern):
                pattern_row=pattern[pattern_index]

            if pattern_row is not None:
                step=2*math.pi/100
                for i in range(5):
                    bar_x=int(screen_size.x//2+math.sin(theta+i*step)*screen_size.x//2-0.00001)
                    
                    image.put_rgba(bar_x,
                                   screen_y,
                                   bg if pattern_row[i]==' ' else fg)
            
            # bg=(0,0,255,255)
            # colour=bg
            # for screen_x in range(screen_size.x):
            #     colour=bg
            #     if screen_x==bar_x:
            #         colour=white
            #     image.put_rgba(screen_x,screen_y,colour)
        
        return {None:image}

    num_frames=250

    all_suffixes=set()
    last_progress=None
    for frame_index in range(num_frames):
        if not g_verbose:
            n=num_frames-frame_index
            sys.stdout.write(str(n))
            if frame_index%16==15: sys.stdout.write('\n')
            else: sys.stdout.write(' ')
            sys.stdout.flush()
            
        for fun_index,fun in enumerate([create_frame_1]):
            images=fun(frame_index)
            for suffix,image in images.items():
                if suffix is None: suffix='.%d'%fun_index
                all_suffixes.add(suffix)
                if options.intermediate_folder is not None:
                    output_path=os.path.join(options.intermediate_folder,
                                             '%s%s.%d.png'% (prototype_name,
                                                             suffix,
                                                             frame_index))
                    image.save_png(output_path)

    print()

    if (options.intermediate_folder is not None and
        options.output_folder is not None):
        for suffix in all_suffixes:
            argv=['ffmpeg',
                  '-y',
                  '-r','50',
                  '-i',os.path.join(options.intermediate_folder,
                                    '%s%s.%%d.png'%(prototype_name,
                                                    suffix)),
                  '-vf','scale=%d:%d,setsar=24/25'%(screen_size.x*2, screen_size.y),
                  '-sws_flags','neighbor',
                  '-pix_fmt','yuv420p',
                  os.path.join(options.output_folder,
                               '%s%s.mp4'%(prototype_name,
                                           suffix))]
            try: subprocess.run(argv,check=True)
            except subprocess.CalledProcessError as e: fatal(str(e))

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.add_argument('--intermediate',dest='intermediate_folder',metavar='FOLDER',help='''where to write intermediate files''')
    parser.add_argument('--output',dest='output_folder',metavar='FOLDER',help='''where to write output files''')
    parser.add_argument('-v','--verbose',action='store_true',help='''be more verbose''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
