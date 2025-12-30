#!/usr/bin/python3

def main():
    num_columns=48
    
    region=bytearray(num_columns*2)
    for i in range(len(region)): region[i]=32

    text=b'LOREM IPSUM DOLOR SIT AMET, CONSECTETUR ADIPISCING ELIT, SED DO EIUSMOD TEMPOR INCIDIDUNT UT LABORE ET DOLORE MAGNA ALIQUA'

    offset=0
    next_text_index=0

    for i in range(100):
        base=offset
        current=bytearray()
        for x in range(num_columns):
            value=region[base+x]
            current.append(value)

        print('%3d: [%s] ; %d'%(i,current.decode('ascii'),offset))

        # scroll
        c=text[next_text_index]
        region[offset+num_columns]=c
        region[offset]=c

        next_text_index+=1
        if next_text_index==len(text): next_text_index=0
        
        offset+=1
        if offset>=num_columns: offset=0

if __name__=='__main__': main()
