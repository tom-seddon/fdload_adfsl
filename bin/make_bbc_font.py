#!/usr/bin/python3
import sys,os,os.path,argparse

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def main2(options):
    with open(options.input_path,'rb') as f: data=f.read()
    if len(data)!=16384: fatal('not 16KB: %s'%options.input_path)

    def write(f):
        for y in range(8):
            f.write('row%ds:\n'%y)
            for ch in range(32,128):
                assert ch>=32 and ch<256
                offset=0x3900+(ch-32)*8+y

                comment='ch %d ($%02x)'%(ch,ch);
                if ch>=32 and ch<127: comment+=" ('%c')"%ch
                comment+=' row %d'%y
        
                value_str=(7*'0'+bin(data[offset+y])[2:])[-8:]
                f.write('    .byte %%%s ; %s\n'%(value_str,comment))

    if options.output_path is not None:
        if options.output_path=='-': write(sys.stdout)
        else:
            with open(options.output_path,'wt') as f: write(f)
            

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()

    parser.add_argument('-o',dest='output_path',metavar='FILE',help='''write data to %(metavar)s, or - for stdout''')
    parser.add_argument('input_path',metavar='FILE',help='''read input from %(metavar)s''')

    main2(parser.parse_args(argv))

##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
