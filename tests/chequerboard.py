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

    prototype_name='chequerboard'

    screen_size=V2(80,168)

    square_size=V2(8,16)

    white=(255,255,255,255)
    black=(0,0,0,255)

    def create_frame_1(frame_index):
        image=zimg.create_rgba(screen_size)

        for screen_y in range(screen_size.y):
            for screen_x in range(screen_size.x):
                colour=black
                fx=((screen_x+frame_index)>>3)
                fy=(screen_y>>4)
                if (fx^fy)&1: colour=white
                image.put_rgba(screen_x,screen_y,colour)
        
        return {None:image}

    num_frames=250
    full_progress='*'*50

    all_suffixes=set()
    for frame_index in range(num_frames):
        if not g_verbose:
            sys.stdout.write('\rBuild: [%-*.*s]'%(
                len(full_progress),
                int(frame_index/(num_frames-1)*len(full_progress)),
                full_progress))
            
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
                  '-vf','scale=%d:%d,setsar=24/25'%(screen_size.x*4, screen_size.y),
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
