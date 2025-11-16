#!/usr/bin/python3
import sys,os,argparse,collections,json,dataclasses

##########################################################################
##########################################################################

# To simplify the disk layout process, side 0 track 0 is reserved entirely
# for data that's possibly going to be read by ADFS: the disk
# metadata, and the *EXECable portion of the !BOOT file.
#
# There's 9 sectors free in this region, 2304 bytes. Given the !BOOT
# encoding, a safe assumption for max initial loader code is 512
# bytes. More could be available in practice, depending on contents
# and load address.
#
# fdload content starts at side 1 track 0 sector 0.
#
# 

##########################################################################
##########################################################################

# TODO: sort out my .inf reading code so it can go by .inf rather than
# .prg

##########################################################################
##########################################################################

# path = path of file on disk, relative to root of working copy.
#
# ident = suffix for the identifier used to refer to this file in
# the 6502 code.

File=collections.namedtuple('File','path ident')

# List of files that go into the build is defined here.
def make_files_list():
    files=[]
    for i in range(10):
        files.append(File(path=r'''beeb/adfsl_fixed_layout/1/$.SCREEN%d'''%i,
                          ident='screen%d'%i))

    return files

##########################################################################
##########################################################################

# https://stackoverflow.com/a/51286749/1618406
class JSONEncoder2(json.JSONEncoder):
    def default(self,o):
        if dataclasses.is_dataclass(o): return dataclasses.asdict(o)
        return super().default(o)

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

def get_exec_part(options):
    with open(options.loader0_path,'rb') as f: data=f.read()

    if len(data)<3:
        fatal('loader0 file too small: %s'%options.input_path)

    load_addr=data[0]|data[1]<<8
    data=bytearray(data[2:])

    while len(data)%4!=0: data.append(0)

    lines=[]
    for i in range(0,len(data),4):
        addr=load_addr+i
        dword=data[i+0]|data[i+1]<<8|data[i+2]<<16|data[i+3]<<24
        stmt='!%s=%s'%(get_smaller_str(addr),get_smaller_str(dword))

        # max BASIC 4 line length is $ee (see
        # https://8bs.com/basic/basic4-b8b6.htm) - leave a bit of
        # slack
        if len(lines)>0 and len(lines[-1])+1+len(stmt)<0xe0:
            assert len(lines[-1])>0
            lines[-1]+=':'+stmt
        else: lines.append(stmt)

    lines.append('CALL%s'%get_smaller_str(load_addr))

    result=bytearray()
    result+=b'*BASIC\r'
    if options.vdu21: result+='VDU21\r'
    for line_index,line in enumerate(lines):
        result+=line.encode('ascii')
        # no harm in having the VDU6 always there
        if line_index==len(lines)-1: result.append(6)
        result.append(13)

    return result

def get_filler(n): return n*b'\x00'

def pad_and_check_budget(data,max_size,description):
    assert isinstance(data,bytearray),type(data)
    
    if len(data)>max_size:
        fatal('%s too large: %d bytes (max is %d; overrun by %d)',
              description,
              len(data),
              len(data)-max_size)

    data+=bytearray(max_size-len(data))

##########################################################################
##########################################################################

@dataclasses.dataclass
class TOCEntry:
    ident:str
    path:str
    index:int
    ltrack:int
    sector:int
    num_bytes:int
# TOCEntry=collections.namedtuple('TOCEntry','ident path index ltrack sector num_bytes')
    
def build_cmd(files,options):
    output_data=bytearray()
    
    exec_data=get_exec_part(options)

    # Provided the *EXEC part is smaller than this, it will fit into
    # track 0, simplifying the pretence that ADFS and fdload have
    # compatible views of the disk.
    #
    # (The ADFS metadata is 7 sectors, so there's 9 sectors left in
    # track 0.)
    pad_and_check_budget(exec_data,9*256,'loader8 in *EXEC form')
    output_data+=exec_data

    # Space for loader1.
    loader1_data=bytearray()
    pad_and_check_budget(loader1_data,4096,'loader1 data')
    output_data+=loader1_data

    # should have filled up to the start of H0 T0 S0.
    assert len(output_data)==(9+16)*256,len(output_data)

    toc=[]
    lsector=32
    for file_index,file in enumerate(files):
        with open(file.path,'rb') as f: file_data=f.read()

        file_size_bytes=len(file_data)
        
        n=file_size_bytes%256
        if n!=0: file_data+=get_filler(256-n)
        assert len(file_data)%256==0

        toc.append(TOCEntry(ident=file.ident,
                            path=file.path,
                            index=file_index,
                            ltrack=lsector//16,
                            sector=lsector%16,
                            num_bytes=file_size_bytes))

        output_data+=file_data
        lsector+=len(file_data)//256

    max_output_data_size=(2*80*16-7)*256
    pad_and_check_budget(output_data,(2*80*16-7)*256,'output big file')

    if options.output_data_path is not None:
        with open(options.output_data_path,'wb') as f: f.write(output_data)

    if options.output_toc_path is not None:
        with open(options.output_toc_path,'wt') as f:
            json.dump(toc,f,indent=4*' ',cls=JSONEncoder2)

##########################################################################
##########################################################################

def constants_cmd(files,options):
    def constants(f):
        for file_index,file in enumerate(files):
            f.write('file_%s=%d ; %s\n'%(file.ident,file_index,file.path))

        f.write('num_files=%d\n'%len(files))

    if options.output_path is None: constants(sys.stdout)
    else:
        with open(options.output_path,'wt') as f: constants(f)

##########################################################################
##########################################################################

def main(argv):
    parser=argparse.ArgumentParser()
    parser.set_defaults(fun=None)

    subparsers=parser.add_subparsers()

    def add_subparser(name,fun,**kwargs):
        subparser=subparsers.add_parser(name,**kwargs)
        subparser.set_defaults(fun=fun)
        return subparser

    constants_subparser=add_subparser('constants',constants_cmd,help='''generate constants source file''')
    constants_subparser.add_argument('--output',metavar='FILE',dest='output_path',help='''write output to %(metavar)s rather than stdout''')

    build_subparser=add_subparser('build',build_cmd,help='''generate big data file''')
    build_subparser.add_argument('--loader0',metavar='FILE',required=True,dest='loader0_path',help='''read loader0 code from %(metavar)s, a C64 .prg''')
    build_subparser.add_argument('--vdu21',action='store_true',help='''add a VDU21 in the *EXECable part''')
    build_subparser.add_argument('--output-data',metavar='FILE',dest='output_data_path',help='''write output to %(metavar)s''')
    build_subparser.add_argument('--output-toc',metavar='FILE',dest='output_toc_path',help='''write TOC JSON to %(metavar)s''')
    
    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    files=make_files_list()
    idents_seen=set()
    for file in files:
        if file.ident in idents_seen:
            fatal('duplicate ident in files list: %s'%file.ident)
        idents_seen.add(file.ident)

    options.fun(files,options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
