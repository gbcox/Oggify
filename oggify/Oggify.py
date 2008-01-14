"""Functions for Oggify operation.

This module provides the external functions for using Oggify operations in
your programs.
"""

import os, os.path, sys, re

class OggifyError(StandardError):
    """Runtime error for Oggify"""
    pass

def _walk_src_tree(root, src_ext, dst_ext):
    symlink_dirs = []
    dirs = {}
    encode = {}
    org_dir = os.getcwd()
    os.chdir(root)
    for current, subdirs, files in os.walk('.'):
        for subdir in subdirs:
            dirs['/'.join((current[2:], subdir))] = None
            if os.path.islink(subdir):
                symlink_dirs.append(subdir)
        for file in files:
            if file.endswith(src_ext):
                src_fname = '/'.join((current[2:], file))
                dst_fname = '.'.join(src_fname.split('.')[:-1] + [dst_ext])
                encode[src_fname] = dst_fname
    os.chdir(org_dir)
    return (encode, dirs)

def _compare_dst_tree(root, src_ext, dst_ext, encode, dirs):
    reencode = {}
    limited_purge = []
    purge = []
    if not os.path.exists(root):
        return (encode, {}, [], [])
    org_dir = os.getcwd()
    os.chdir(root)
    for current, subdirs, files in os.walk('.'):
        dont_walk = []
        for subdir in subdirs:
            if '/'.join((current[2:], subdir)) not in dirs:
                purge.append('/'.join((current[2:], subdir)))
                subdirs.remove(dir)

        for file in files:
            src_eq = '/'.join((current[2:],
                '.'.join(file.split('.')[:-1] + [src_extension])))
            if src_eq in encode:
                if not file.endswith(extension):
                    limited_purge.append('/'.join((current[2:], file)))
                else:
                    reencode[src_eq] = encode[src_eq]
                    del encode[src_eq]
            else:
                purge.append('/'.join((current[2:], file)))
    os.chdir(org_dir)
    return (encode, reencode, limited_purge, purge)

def diff(src_dir, dst_dir, src_ext, dst_ext):
    """Produce action structures for Oggify.
        src_dir - the root of the source tree
        src_ext - the extension to use for source files, ie: 'flac'
        dst_dir - the root for the output tree
        dst_ext - the extension to use for destination files, ie: 'ogg'
    
    Returns (encode, reencode, limited_purge, purge):
        encode - A dictionary of "source file" => "destination file" where
            source file is all of the files in src_dir with src_ext that do
            not exist in dst_dir.
        reencode - A dictionary of "source file" => "destination file" where
            source file is all of the files in src_dir with src_ext that do
            exist in dst_dir with dst_ext
        limited_purge - A list of files in dst_dir that are in src_dir with
            src_ext, but do not have dst_ext.
        purge - A list of files and directories that do not exist in src_dir
            with src_ext. Any non-src_ext files will wind up here.
    """
    (encode, src_dirs) = _walk_src_tree(src_dir, src_ext, dst_ext)
    return _compare_dst_tree(dst_src, src_ext, encode, src_dirs)

def list_plugins(type):
    from oggify import plugins
    plugin_dir = plugins.__path__[0]
    contents = os.listdir(plugin_dir)
    plugins = []
    for filename in contents:
        if re.search(r'\.py$', filename) and filename != '__init__.py':
            plugins.append(filename.split('.')[0])
    for plugin in plugins:
        mod = __import__('.'.join(('oggify', 'plugins', plugin)), fromlist=[''])
        codec = mod.Codec()
        if codec.type != type and codec.type != 'both':
            plugins.remove(plugin)
    return plugins

def load_plugin(plugin, type):
    """Load an oggify plugin by string.
        plugin - string of the plugin
        type - 'input' or 'output'

    Raises an OggifyError if the plugin requested does not support the type.

    Returns oggify.plugins.Codec of the plugin.
    """
    mod = __import__('.'.join(('oggify', 'plugins', plugin)),
            fromlist=[''])
    codec = mod.Codec()
    if codec.type != type and codec.type != 'both':
        raise OggifyError("%s is not a %s plugin!" % (plugin, type))
    return codec

def process_file(decoder, encoder, src_file, dst_file, quality,
        verbosity=0, temp_file=None):
    """Encode a file using the correct source format file.
        decoder - oggify.plugins.Codec, type 'input'
        encoder - oggfiy.plugins.Codec, type 'output'
        src_file - string, source file (from oggify.Oggify.diff)
        dst_file - string, destination file (from oggify.Oggify.diff)
        quality - int, 0 - 10. Quality to use for encoding (see oggenc(1))
        verbosity - boolean, Determines how much is printed to sys.stdout
        temp_file - string, filename to use while encoding to handle 
                    interrupts

    Raises an OggifyError if the decode or encode process does not return
    successfully.

    This properly calls the Codec objects to take src_file to dst_file.
    """

    output = None
    if verbosity:
        output = sys.stdout
    print "Encoding %s to %s" % (src_file, dst_file)

    dir = os.path.dirname(dst_file)
    os.makedirs(dir)
    decoder_process = decoder.decode(src_file)
    if temp_file == None:
        temp_file = os.tempnam()
    encoder_process = encoder.encode(temp_file, quality,
            decoder_process.pipe, output)
    encoder_process.wait()
    if encoder_process.returncode != 0 or decoder_process.returncode != 0:
        raise OggifyError("Encode/decode process failure")
    os.rename(temp_file, dst_file)
