# Motorola SM6375 Linux 6.1 builder

Builds Fogos and Rhodep from Motorola's `MMI-W1UOS36H.35-39-7` Linux 6.1.145 base with the retained APR/Q6 audio stack and the matching board drivers.

Initialize the [kernel manifest](https://github.com/Motorola-Sedona61/kernel_manifest), then run from the workspace root:

```sh
./build.sh FOGOS
./build.sh RHODEP
```

The commands run sequentially. Each produces a complete Android prebuilt tree at `prebuilt/BOARD/6.1`, containing `Image`, the merged base DTB, the board DTBO image, first-stage and vendor modules, load lists, the board blocklist, and exported kernel/vendor UAPI headers. The shared Motorola module repository includes Fogos drivers under `legacy/fogos` and the newer modules used by Rhodep.

Run `./build/setup.sh` once after syncing to install the pinned Python header-export dependency. LLVM 18 and pahole must be installed. Override the LLVM directory with `--llvm` or `LLVM_DIR`, and pahole with `PAHOLE` if necessary. Jobs default to the host CPU count, capped at 192. A workspace lock prevents simultaneous builds from overwriting external-module outputs.

```sh
./build.sh FOGOS --plan
./build.sh FOGOS --jobs 32
./build.sh RHODEP --prebuilt /path/to/prebuilt/6.1
./build.sh FOGOS --android-tree /path/to/lineage
```

`--android-tree` additionally installs the output in `device/motorola/DEVICE-kernel/6.1`. Use an ordinary prebuilt checkout rather than a symlink to a frozen staging directory. Existing generated output is retained as `6.1.previous` before replacement.

The kernel manifest pins every source project and the header/DTBO tools. It preserves Motorola ancestry in the kernel, display and graphics histories. The builder does not require proprietary firmware to compile; firmware remains part of the Android vendor repositories.

See the [build guide](https://github.com/Motorola-Sedona61/guide) for host packages and ROM build instructions.
