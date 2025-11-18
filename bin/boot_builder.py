#!/usr/bin/python3
import sys,os,argparse,collections,json,dataclasses,importlib,importlib.util

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

##########################################################################
##########################################################################

# 1. When running boot_builder.py, use --list to supply the Python
# list file - a file with Python code in it that specifies the files
# to include on the disk.
#
# 2. Use "boot_builder.py constants" to generate a .s65 with constants
# for the file indexes. This gets included by any of the consuming
# code.
#
# 3. Use "boot_builder.py build" to build the actual big !BOOT file.
# This takes paths to loader0 (C64 .PRG bootstrap program, poked into
# RAM from BASIC then executed) and loader1 (C64 .PRG second loader
# program, loaded from disk then executed). The binary TOC is appended
# to loader1, which is assumed to the fdload code plus anything else
# and start the actual thing running.
#
# Perhaps obviously, the file list should be the same for the
# constants and build run in a particular build.
#
# (Max size for loader0 is 512 bytes; max size for loader1+TOC is 4
# KB.)
#
# The big !BOOT file is 653,568 bytes, and will fit on an empty ADFS L
# disk.

# boot_builder.py can produce some additional output:
#
# . binary format TOC, for use by test code
#
# . JSON format TOC, vaguely human readable
#
# . BeebLink files, numbered, one per file on disk, for testing
# purposes. plus $.COUNT, a 1-byte file containing 1 byte: the number
# of files

##########################################################################
##########################################################################

# path = path of file on disk, relative to root of working copy.
#
# ident = suffix for the identifier used to refer to this file in
# the 6502 code.

File=collections.namedtuple('File','path ident')

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

def makedirs(path):
    if not os.path.isdir(path): os.makedirs(path)

##########################################################################
##########################################################################

PRG=collections.namedtuple('PRG','addr data')

def load_prg(path):
    with open(path,'rb') as f: data=f.read()

    if len(data)<3: fatal('file too small to be a C64 .PRG: %s'%path)

    return PRG(addr=data[0]|data[1]<<8,data=bytearray(data[2:]))

##########################################################################
##########################################################################

def get_smaller_str(x):
    xs='&%X'%x
    
    dword=int(x&(1<<31)-1)
    if x&(1<<31): dword+=-(1<<31)
    ds='%d'%dword

    return ds if len(ds)<len(xs) else xs

def get_exec_part(options):
    loader0=load_prg(options.loader0_path)

    while len(loader0.data)%4!=0: loader0.data.append(0)

    lines=[]
    for i in range(0,len(loader0.data),4):
        addr=loader0.addr+i
        dword=(loader0.data[i+0]|
               loader0.data[i+1]<<8|
               loader0.data[i+2]<<16|
               loader0.data[i+3]<<24)
        stmt='!%s=%s'%(get_smaller_str(addr),get_smaller_str(dword))

        # BASIC 4 input buffer size is $ee (see
        # https://8bs.com/basic/basic4-b8b6.htm) - leave a bit of
        # slack
        if len(lines)>0 and len(lines[-1])+1+len(stmt)<0xe0:
            assert len(lines[-1])>0
            lines[-1]+=':'+stmt
        else: lines.append(stmt)

    lines.append('CALL%s'%get_smaller_str(loader0.addr))

    result=bytearray()
    result+=b'*BASIC\r'
    if options.vdu21:
        result+=b'V.12,23,1;0;0;0;0,21\r'
        result+=b'V.6:P."LOADING...";:V.21\r'
    for line_index,line in enumerate(lines):
        result+=line.encode('ascii')
        # no harm in having the VDU6 always there
        if line_index==len(lines)-1: result.append(6)
        result.append(13)

    return result

def get_filler(n): return n*b'\x00'

def check_budget(data,max_size,description):
    
    if len(data)>max_size:
        fatal('too large: %d bytes (max is %d; overrun by %d): %s',
              description,
              len(data),
              len(data)-max_size)

def check_budget_and_pad(data,max_size,description):
    assert isinstance(data,bytearray),type(data)

    check_budget(data,max_size,description)

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

##########################################################################
##########################################################################
    
def build_cmd(files,options):
    exec_data=get_exec_part(options)

    # Provided the *EXEC part is smaller than this, it will fit into
    # track 0, simplifying the pretence that ADFS and fdload have
    # compatible views of the disk.
    #
    # (The ADFS metadata is 7 sectors, so there's 9 sectors left in
    # track 0.)
    check_budget_and_pad(exec_data,9*256,'loader8 in *EXEC form')

    fdload_data=bytearray()
    
    # Space for loader1.
    loader1=load_prg(options.loader1_path)
    check_budget_and_pad(loader1.data,4096,'loader1 data')
    fdload_data+=loader1.data

    toc=[]
    file_contents=[]
    
    lsector=32
    for file_index,file in enumerate(files):
        with open(file.path,'rb') as f: file_data=f.read()

        file_size_bytes=len(file_data)

        if file_size_bytes==0: fatal('unsupported 0 byte file: %s'%file.path)

        check_budget(file_data,65536,file.path)

        toc.append(TOCEntry(ident=file.ident,
                            path=file.path,
                            index=file_index,
                            ltrack=lsector//16,
                            sector=lsector%16,
                            num_bytes=len(file_data)))
        file_contents.append(file_data)

        n=file_size_bytes%256
        if n!=0: file_data+=get_filler(256-n)
        assert len(file_data)%256==0

        fdload_data+=file_data
        lsector+=len(file_data)//256

    assert len(toc)==len(file_contents)
    for i in range(len(toc)): assert toc[i].num_bytes==len(file_contents[i])

    max_fdload_data_size=(2*80-1)*16*256
    check_budget_and_pad(fdload_data,max_fdload_data_size,'output big file')

    # The output big file is in fdload logical sector order. Rearrange
    # so that it is in the ADFS sector order expected by adf_create.
    output_data=bytearray()
    for side in range(2):
        for track in range(80):
            if track==0 and side==0:
                # there is no fdload data in this area.
                continue

            ltrack=track*2+side-1
            assert ltrack>=0 and ltrack<159
            
            i=ltrack*4096
            j=len(output_data)
            if i>len(fdload_data): output_data+=bytearray(4096)
            else: output_data+=fdload_data[i:i+4096]

            # if track>=1:
            #     output_data[j+0]=side
            #     output_data[j+1]=track

    # Prepend the 9 sectors of loader0.
    output_data=exec_data+output_data
    assert len(output_data)==(2*80*16-7)*256

    if options.output_data_path is not None:
        with open(options.output_data_path,'wb') as f: f.write(output_data)

    if options.output_toc_json_path is not None:
        toc_json={
            'num_files':len(toc),
            'files':toc,
        }
        with open(options.output_toc_json_path,'wt') as f:
            json.dump(toc_json,f,indent=4*' ',cls=JSONEncoder2)

    if options.output_toc_binary_path is not None:
        toc_binary=bytearray()
        toc_binary.append(len(toc))
        for entry in toc:
            assert entry.ltrack>=0 and entry.ltrack<160
            toc_binary.append(entry.ltrack)

            assert entry.sector>=0 and entry.sector<16
            toc_binary.append(entry.sector)

            toc_binary.append(-entry.num_bytes&0xff)
            toc_binary.append(-entry.num_bytes>>8&0xff)
            
        with open(options.output_toc_binary_path,'wb') as f:
            f.write(toc_binary)

    if options.output_beeblink_path is not None:
        makedirs(options.output_beeblink_path)
        for i in range(len(file_contents)):
            with open(os.path.join(options.output_beeblink_path,
                                     '''$.%d'''%i),'wb') as f:
                f.write(file_contents[i])

        count=bytearray()
        count.append(len(file_contents))
        with open(os.path.join(options.output_beeblink_path,'''$.COUNT'''),
                  'wb') as f:
            f.write(count)

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
    parser.add_argument('-l','--list',metavar='FILE',dest='list_py_path',required=True,help='''use Python script %(metavar)s to get files list''')
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
    build_subparser.add_argument('--loader1',metavar='FILE',required=True,dest='loader1_path',help='''read loader1 code from %(metavar)s, a C64 .prg''')
    build_subparser.add_argument('--vdu21',action='store_true',help='''add a VDU21 in the *EXECable part''')
    build_subparser.add_argument('--output-data',metavar='FILE',dest='output_data_path',help='''write output to %(metavar)s''')
    build_subparser.add_argument('--output-toc-json',metavar='FILE',dest='output_toc_json_path',help='''write TOC JSON to %(metavar)s''')
    build_subparser.add_argument('--output-toc-binary',metavar='FILE',dest='output_toc_binary_path',help='''write TOC binary to %(metavar)s''')
    build_subparser.add_argument('--output-beeblink',metavar='PATH',dest='output_beeblink_path',help='''write numbered BeebLink-friendly files to %(metavar)s''')
    
    options=parser.parse_args(argv)
    if options.fun is None:
        parser.print_help()
        sys.exit(1)

    # https://stackoverflow.com/a/54956419/1618406
    spec=importlib.util.spec_from_file_location('file_list',
                                                options.list_py_path)
    file_list_module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(file_list_module)

    files=file_list_module.make_files_list()
    idents_seen=set()
    for file in files:
        if file.ident in idents_seen:
            fatal('duplicate ident in files list: %s'%file.ident)
        idents_seen.add(file.ident)

    options.fun(files,options)
    
##########################################################################
##########################################################################

if __name__=='__main__': main(sys.argv[1:])
