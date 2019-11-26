# llvm-dash

[LLVM](http://llvm.org/) Compiler Infrastructure docset for Dash.

## Requirements

- `make`
- `wget`
- `python3`

LLVM is required to be built, with documentation enabled as described below.

## Configuring LLVM To Build Docs

Only a few tweaks are needed to build documentation via LLVM.

First, make sure you have Sphinx installed via Python:

    pip3 install sphinx

Next, assuming you want Doxygen-generated docs to be part of the docset, you need 
to configure Doxygen:

Modify `<llvm_src_dir>/docs/doxygen.cfg.in`:

- Set `GENERATE_DOCSET = YES`
- Set `GENERATE_TAGFILE = llvm.tags`
- Set `DISABLE_INDEX = YES`
- Set `SEARCHENGINE = NO`

Finally, build LLVM with the following flags:

- `-DLLVM_BUILD_DOCS=ON`
- `-DLLVM_ENABLE_SPHINX=ON`
- `-DLLVM_ENABLE_DOXYGEN=ON` (if you want Doxygen docs)
- `-DLLVM_INCLUDE_DOCS=ON`
- `-DLLVM_BUILD_DOCS=ON`

NOTE: If you want to build LLVM in a way that matches my environment, also do the following:

- In the `llvm-project` directory, run `mkdir -p build/host`
- Create an install path:
    - `mkdir -p ~/.local/share/llvm/<llvm version>`
- From the `llvm-project` root; `cd build/host`
- Finally, kick off the build:


    cmake \
        -DCMAKE_INSTALL_PREFIX=$HOME/.local/share/llvm/<llvm version> \
        <build flags> \
        ../../llvm \
    && ninja \
    && ninja install
    
This will build and install to `~/.local/share/llvm/<version>`, which you will need later.
Replace `ninja` with `make`, if you aren't using Ninja to build.

You can then use the `ASSUME_LUMEN_STYLE_BUILD=true` as described later, which simplifies things a bit.

NOTE: This may take awhile, mainly if Doxygen is enabled, but once it is finished the rest is easy.

## Generating the docset

Now that the doc sources are generated, we need to generate the index and docset.

If you followed my build recommendations from above (building in `build/host` and installing to 
`~/.local/share/llvm/<version>`, then you can run the following to build the docs:

    make LLVM_PREFIX=$HOME/.local/share/llvm/<version> ASSUME_LUMEN_STYLE_BUILD=true docs

If you used your own approach, then drop `ASSUME_LUMEN_STYLE_BUILD` and set `LLVM_PREFIX` appropriately:

    make LLVM_PREFIX=<path to LLVM installation> docs

## How it works

The tool uses `llvm-config` found in `$LLVM_PREFIX/bin` to detect information about the LLVM we're building
a docset for, namely the version, and the source root (i.e. the directory in which the sources can be found).
If the LLVM installation has no sources present, then the build will fetch docs for that version from the internet,
but will not generate Doxygen docs, as there will be no tag file for the index.

Once the sources and the docset skeleton are prepared, the script copies the docs to the docset, and then
constructs an index by traversing all the documentation. See `bin/index.py` for details.

## Caveats

Building the docset with Doxygen produces a huge docset, like 5gb+ huge. If you don't need Doxygen, then export
`NO_DOXYGEN=true` in the shell environment before running `make docs`.
