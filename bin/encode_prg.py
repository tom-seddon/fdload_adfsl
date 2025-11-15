#!/usr/bin/python3
import sys,os,argparse

##########################################################################
##########################################################################

# TODO: sort out my .inf reading code so it can go by .inf rather than
# .prg

##########################################################################
##########################################################################

def fatal(msg):
    sys.stderr.write('FATAL: %s\n'%msg)
    sys.exit(1)

##########################################################################
##########################################################################

def get_smaller_str(x):
    xs='&%X'%x
    
    dword=int(x&(1<<31)-1)
    if x&(1<<31): dword+=-(1<<31)
    ds='%d'%dword

    return ds if len(ds)<len(xs) else xs

def main2(options):
    with open(options.input_path,'rb') as f: data=f.read()

    if len(data)<3: fatal('file too small: %s'%options.input_path)

    load_addr=data[0]|data[1]<<8
    data=bytearray(data[2:])

    while len(data)%4!=0: data.append(0)

    lines=[]
    for i in range(0,len(data),4):
        addr=load_addr+i
        dword=data[i+0]|data[i+1]<<8|data[i+2]<<16|data[i+3]<<24
        stmt='!%s=%s'%(get_smaller_str(addr),get_smaller_str(dword))

        if len(lines)>0 and len(lines[-1])+1+len(stmt)<0xe0:
            assert len(lines[-1])>0
            # max BASIC 4 line length is $ee (see
            # https://8bs.com/basic/basic4-b8b6.htm) - leave a bit of
            # slack
            lines[-1]+=':'+stmt
        else: lines.append(stmt)

    lines.append('CALL%s'%get_smaller_str(load_addr))

    if options.output_path is None:
        for line in lines: print(line)
    else:
        mode='ab' if options.append else 'wb'
        with open(options.output_path,mode) as f:
            # unfortunately seems you can't actually type in a VDU21,
            # so there'll always be at least a little bit of muck.
            f.write(b'*BASIC\r')
            if options.hidden: f.write(b'VDU21\r')
            for line_index,line in enumerate(lines):
                f.write(line.encode('ascii'))
                if options.hidden:
                    if line_index==len(lines)-1:
                        f.write(b'\x06')
                f.write(b'\r')

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    
    parser.add_argument('input_path',metavar='FILE',help='''read C64 .prg data from %(metavar)s''')
    parser.add_argument('--append',action='store_true',help='''if writing to a file, append rather than overwrite''')
    parser.add_argument('--hidden',action='store_true',help='''embed VDU21/VDU6 so the output looks a bit tidier''')
    parser.add_argument('-o','--output-path',metavar='FILE',help='''write output to %(metavar)s. Output written to stdout may not redirect correctly''')

    main2(parser.parse_args(argv))
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
