// Builds only independent-run wrappers plus the byte-identical frozen KSSD
// sources. Every executed command and compiler output is retained in OUT_DIR
// and printed as Cargo warnings for the outer verbose build log.
use std::env;
use std::fs::OpenOptions;
use std::io::Write;
use std::path::{Path, PathBuf};
use std::process::Command;

fn quote(s: &str) -> String {
    if s.chars().all(|c| c.is_ascii_alphanumeric() || "_./-=+:".contains(c)) {
        s.to_owned()
    } else {
        format!("'{}'", s.replace('\'', "'\\''"))
    }
}
fn invoke(program: &str, args: &[String], out: &Path) {
    let line = std::iter::once(quote(program))
        .chain(args.iter().map(|x| quote(x))).collect::<Vec<_>>().join(" ");
    println!("cargo:warning=SD_NATIVE_COMMAND {}", line);
    let output = Command::new(program).args(args).output()
        .unwrap_or_else(|e| panic!("Cannot execute {}: {}", program, e));
    let mut log = OpenOptions::new().create(true).append(true)
        .open(out.join("native_commands.log")).expect("native command log");
    writeln!(log, "$ {}", line).unwrap();
    writeln!(log, "exit={:?}", output.status.code()).unwrap();
    for (label, bytes) in [("stdout", &output.stdout), ("stderr", &output.stderr)] {
        let text = String::from_utf8_lossy(bytes);
        writeln!(log, "{}:\n{}", label, text).unwrap();
        for line in text.lines() {
            println!("cargo:warning=SD_NATIVE_{} {}", label.to_uppercase(), line);
        }
    }
    assert!(output.status.success(), "Native build failed: {}", line);
}
fn compile_c(root: &Path, out: &Path, source: &str, object: &str, fixed_k: Option<usize>) -> PathBuf {
    let target = out.join(object);
    let mut args = vec!["-O3".into(), "-march=native".into(), "-std=c11".into(),
        "-fPIC".into(), "-Wall".into(), "-Wextra".into(),
        format!("-I{}", root.join("kssd-array/include").display()),
        format!("-I{}", root.join("kssd-array/src").display())];
    if let Some(k) = fixed_k { args.push(format!("-DKSSD_ARRAY_FIXED_K={}", k)); }
    args.extend(["-c".into(), root.join(source).display().to_string(),
        "-o".into(), target.display().to_string()]);
    invoke("/usr/bin/gcc", &args, out);
    target
}
fn main() {
    let root = PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").expect("manifest dir"));
    let out = PathBuf::from(env::var_os("OUT_DIR").expect("OUT_DIR"));
    let run = root.parent().expect("independent run root");
    assert!(out.starts_with(run), "OUT_DIR must remain inside this independent run");
    for source in ["kssd-array/include", "kssd-array/src", "kssd_context.c",
                   "kssd_score.c", "gm.cpp", "gm_loader_exact.inc"] {
        println!("cargo:rerun-if-changed={}", root.join(source).display());
    }
    let mut objects = vec![
        compile_c(&root, &out, "kssd-array/src/kssd_array.c", "kssd_array.o", None),
        compile_c(&root, &out, "kssd-array/src/permutation.c", "permutation.o", None),
        compile_c(&root, &out, "kssd_context.c", "kssd_context.o", None),
        compile_c(&root, &out, "kssd_score.c", "kssd_score21.o", Some(21)),
        compile_c(&root, &out, "kssd_score.c", "kssd_score31.o", Some(31)),
    ];
    let gm_object = out.join("gm.o");
    let gm_args = vec!["-O3".into(), "-march=native".into(), "-std=c++17".into(),
        "-fPIC".into(), "-Wall".into(), "-Wextra".into(),
        format!("-I{}", root.display()),
        format!("-I{}", root.join("GreedyMini").display()),
        "-c".into(), root.join("gm.cpp").display().to_string(),
        "-o".into(), gm_object.display().to_string()];
    invoke("/usr/bin/g++", &gm_args, &out);
    objects.push(gm_object);
    let mut archive_args = vec!["crs".into(), out.join("libsd_native.a").display().to_string()];
    archive_args.extend(objects.iter().map(|x| x.display().to_string()));
    invoke("/usr/bin/ar", &archive_args, &out);
    println!("cargo:rustc-link-search=native={}", out.display());
    println!("cargo:rustc-link-lib=static=sd_native");
    println!("cargo:rustc-link-lib=dylib=stdc++");
    println!("cargo:rustc-link-lib=dylib=crypto");
}
