
import argparse
import os
import random
import struct


from ..common import code_file
from ..common import frame


ENCRYPTED_END = '.MSecret'
BLOCK_SIZE = 1024
BITSTRUCT = struct.Struct('B')
FIRST_WRITE = BITSTRUCT.pack(0)
SECOND_WRITE = BITSTRUCT.pack(0xff)


def parse_args(commands):
    """Parse program arguments."""

    yes_no = {'yes': True, 'no': False}
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--command',
        required=True,
        type=str,
        choices=sorted(commands.keys()),
        help='encrypt or decrypt or delete the source file/dir',
    )
    parser.add_argument(
        '--src-file',
        required=True,
        type=str,
        help='source file to encrypt or decrypt or delete (command)',
    )
    parser.add_argument(
        '--dst-file',
        default=None,
        type=str,
        help="destination file to write there the encryption or decryption.",
    )
    parser.add_argument(
        '--delete',
        default=sorted(yes_no.keys())[0],
        type=str,
        choices=sorted(yes_no.keys()),
        help='if you want to delete the source file write yes.',
    )
    parser.add_argument(
        '--recursive',
        default=sorted(yes_no.keys())[0],
        type=str,
        choices=sorted(yes_no.keys()),
        help='yes if you want to do the command to dirs inside dirs?',
    )
    parser.add_argument(
        '--passphrase',
        default=None,
        type=str,
        help='%s%s' % (
            'secret passphrase, ',
            'if not specified will be acquired by user interface',
        ),
    )

    args = parser.parse_args()
    args.delete = yes_no[args.delete]
    args.recursive = yes_no[args.recursive]
    return args


def encrypt(password, src, dst, delete, recur):
    if password is None:
        password = frame.Show_Frame(src)
    if dst is None:
        dst = '%s%s' % (src, ENCRYPTED_END)
    encrypt_dir_or_file(
        password,
        src,
        dst,
        recur,
        delete,
    )


def decrypt(password, src, dst, delete, recur):
    if password is None:
        password = frame.Show_Frame(src)
    if dst is None:
        dst = without_encrypted_ending(src)
    decrypt_dir_or_file(
        password,
        src,
        dst,
        recur,
        delete
    )


def encrypt_file(first_file, codefile):
    with open(first_file, 'rb') as fh:
        with code_file.MyOpen(codefile, 'w') as cf:
            while True:
                tmp = fh.read(BLOCK_SIZE)
                if not tmp:
                    break
                cf.write(tmp)


def encrypt_dir_or_file(password, src, dst, recursive, delete):
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        for file in os.listdir(src):
            if os.path.isdir(os.path.join(src, file)):
                if recursive:
                    encrypt_dir_or_file(
                        password,
                        os.path.join(src, file),
                        os.path.join(
                            dst,
                            '%s%s' % (file, ENCRYPTED_END),
                        ),
                        recursive,
                        delete,
                    )

            else:
                encrypt_file(
                    os.path.join(src, file),
                    code_file.CodeFile(
                        os.path.join(
                            dst,
                            '%s%s' % (file, ENCRYPTED_END),
                        ),
                        password,
                    ),
                )
                if delete:
                    delete_file_properly(os.path.join(src, file))
        if delete and recursive:
            os.rmdir(src)
    else:
        encrypt_file(src, code_file.CodeFile(dst, password))
        if delete:
            delete_file_properly(src)


def decrypt_file(codefile, file_name):
    with code_file.MyOpen(codefile, 'r') as cf:
        with open(file_name, 'w') as fh:
            while True:
                text = cf.read(BLOCK_SIZE)
                if not text:
                    break
                fh.write(text)


def decrypt_dir_or_file(password, src, dst, recursive, delete):
    if os.path.isdir(src):
        if not os.path.exists(dst):
            os.makedirs(dst)
        for file in os.listdir(src):
            if os.path.isdir(os.path.join(src, file)):
                if recursive:
                    decrypt_dir_or_file(
                        password,
                        os.path.join(src, file),
                        os.path.join(
                            dst,
                            without_encrypted_ending(file),
                        ),
                        recursive,
                        delete,
                    )
            else:
                decrypt_file(
                    code_file.CodeFile(os.path.join(src, file), password),
                    os.path.join(
                        dst,
                        without_encrypted_ending(file),
                    ),
                )
                if delete:
                    delete_file_properly(os.path.join(src, file))
        if delete and recursive:
            os.rmdir(src)
    else:
        decrypt_file(code_file.CodeFile(src, password), dst)
        if delete:
            delete_file_properly(src)


def without_encrypted_ending(name):
    if name[-len(ENCRYPTED_END):] == ENCRYPTED_END:
        return name[:-len(ENCRYPTED_END)]
    return name


def delete_file_or_dir_properly(file, recursive):
    if os.path.isdir(file):
        for f in os.listdir(file):
            if os.path.isdir(file):
                if recursive:
                    delete_file_or_dir_properly(
                        os.path.join(file, f),
                        recursive,
                    )
            else:
                delete_file_properly(os.path.join(file, f))
        if recursive:
            os.rmdir(file)
    else:
        delete_file_properly(file)


def write_all_file(fh, what_to_write, left_to_write, block_size=BLOCK_SIZE):
    fh.seek(0, 0)
    while left_to_write > 0:
        fh.write(what_to_write * block_size)
        left_to_write -= block_size


def delete_file_properly(file, block_size=BLOCK_SIZE):
    ''' len_file - the length of the data that is written in the file.
    file - the name of the file we want to encrypt

    writing to all file 16 times:
    first byte - 0, second byte - 0xff and random byte'''
    len_file = os.path.getsize(file)
    with open(file, 'w') as fh:
        write_all_file(
            fh,
            FIRST_WRITE,
            len_file,
            block_size,
        )
        write_all_file(
            fh,
            SECOND_WRITE,
            len_file,
            block_size,
        )
        for i in range(6):
            write_all_file(
                fh,
                BITSTRUCT.pack(
                    random.randint(
                        0,
                        255,
                    )
                ),
                len_file,
                block_size,
            )

    os.remove(file)


def main():
    commands = {'encrypt': encrypt, 'decrypt': decrypt, 'delete': delete_file_or_dir_properly}
    args = parse_args(commands)
    if args.command == 'delete':
        commands[args.command](args.src_file, args.recursive)
    else:
        commands[args.command](
            args.passphrase,
            args.src_file,
            args.dst_file,
            args.delete,
            args.recursive,
        )


if __name__ == '__main__':
    main()