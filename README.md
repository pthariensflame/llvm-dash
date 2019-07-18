# llvm-dash

[LLVM](http://llvm.org/) Compiler Infrastructure docset for Dash.

## Requirements

- `make`
- `wget`
- `python`

LLVM is required, preferably via `llvmenv`, but if `llvm-config` is on the
PATH, you can use any installed version you may have, as long as the source
files for the build are available on the machine. You can verify this by
running `llvm-config --src-root` and checking the resulting path.

The generator can also fetch LLVM sources, but this precludes building the
Doxygen docs, since the necessary tag file will not be present.

To include Doxygen docs in the docset, you need to do two things:

- Modify `<llvm_src_dir>/docs/doxygen.cfg.in` and:
    - Set `GENERATE_TAGFILE = llvm.tag`
- Then, build LLVM with `-DLLVM_BUILD_DOCS=ON`

## Generating the docset

Once you've met the requirements above, just run:

    make docs

Simple as that!

If you have `llvmenv` installed, it will use the current LLVM build for its
source, rather than fetching LLVM. 

You may also export `LLVM_VERSION` explicitly to build a specific version of
LLVM docs.
