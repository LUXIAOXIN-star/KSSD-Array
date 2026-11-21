use std::{env, path::PathBuf, process::Command};
fn main() {
    let root=PathBuf::from(env::var_os("CARGO_MANIFEST_DIR").unwrap()).parent().unwrap().to_path_buf();
    let out=PathBuf::from(env::var_os("OUT_DIR").unwrap());
    let cc=env::var("CC").unwrap_or("/usr/bin/gcc".into());
    let mut objects=vec![];
    let inputs=[
        ("core",root.join("third_party/kssd-array/src/kssd_array.c"),None),
        ("permutation",root.join("third_party/kssd-array/src/permutation.c"),None),
        ("context",root.join("kssd_adapter/context.c"),None),
        ("k19",root.join("kssd_adapter/kernel.c"),Some(19)),
        ("k21",root.join("kssd_adapter/kernel.c"),Some(21)),
        ("k31",root.join("kssd_adapter/kernel.c"),Some(31)),
    ];
    for (name,input,k) in inputs {
        println!("cargo:rerun-if-changed={}",input.display());
        let object=out.join(format!("{name}.o"));
        let mut c=Command::new(&cc);
        c.args(["-O3","-march=native","-std=c11","-Wall","-Wextra","-Werror","-fPIC"]);
        c.arg("-I").arg(root.join("third_party/kssd-array/include"));
        c.arg("-I").arg(root.join("third_party/kssd-array/src"));
        if let Some(k)=k {c.arg(format!("-DKSSD_ARRAY_FIXED_K={k}"));}
        c.arg("-c").arg(&input).arg("-o").arg(&object);
        println!("cargo:warning=Native command: {c:?}");
        assert!(c.status().unwrap().success(),"C build failed");
        objects.push(object);
    }
    println!("cargo:rerun-if-changed={}",root.join("third_party/kssd-array/include").display());
    println!("cargo:rerun-if-env-changed=CC");
    let lib=out.join("libkssd_review.a");
    assert!(Command::new("/usr/bin/ar").arg("crs").arg(&lib).args(objects).status().unwrap().success());
    println!("cargo:rustc-link-search=native={}",out.display());
    println!("cargo:rustc-link-lib=static=kssd_review");
}
