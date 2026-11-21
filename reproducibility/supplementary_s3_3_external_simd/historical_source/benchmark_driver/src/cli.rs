use crate::*;
use serde_json::json;
use std::{collections::BTreeMap, fs::{self,OpenOptions}, io::{BufWriter,Write}, path::{Path,PathBuf}};

fn write_new(path:&Path,bytes:&[u8])->Result<()> {
    let mut f=OpenOptions::new().write(true).create_new(true).open(path).map_err(|e|e.to_string())?;
    f.write_all(bytes).map_err(|e|e.to_string())
}
fn run(experiment:Experiment)->Result<()> {
    let mut args=std::env::args().skip(1);let mut options=BTreeMap::new();
    let mut measure=false;let mut allow_large=false;
    while let Some(arg)=args.next(){
        match arg.as_str(){
            "--help"=>{
                println!("{} --input FILE --k 19|21|31 --method METHOD --out NEW_DIRECTORY [--w W --mode strict|weak] [--measure] [--allow-large]\nA/B methods: kssd, seq-hash; C: kssd, simd-minimizers. Default: correctness only, <=1,000,000 bases. B/C require --w and --mode. Output must be below this framework's results/.",experiment.name());
                return Ok(())
            },
            "--measure"=>{if measure{return Err("duplicate --measure".into())}measure=true;},
            "--allow-large"=>{if allow_large{return Err("duplicate --allow-large".into())}allow_large=true;},
            "--input"|"--k"|"--method"|"--out"|"--w"|"--mode"=>{
                let value=args.next().ok_or(format!("missing value for {arg}"))?;
                if options.insert(arg,value).is_some(){return Err("duplicate option".into())}
            },
            _=>return Err(format!("unknown option: {arg}"))
        }
    }
    let required=|key:&str|options.get(key).cloned().ok_or(format!("missing {key}; see --help"));
    let k=required("--k")?.parse::<usize>().map_err(|e|e.to_string())?;
    let method=match required("--method")?.as_str(){"kssd"=>Method::Kssd,"seq-hash"=>Method::SeqHash,"simd-minimizers"=>Method::SimdMinimizers,_=>return Err("unknown method".into())};
    let (mode,w)=if experiment==Experiment::A {
        if options.contains_key("--w")||options.contains_key("--mode"){return Err("A has canonical scores but no window/mode parameter".into())}
        (Mode::Strict,None)
    }else{
        let mode=match required("--mode")?.as_str(){"strict"=>Mode::Strict,"weak"=>Mode::Weak,_=>return Err("mode must be strict or weak".into())};
        (mode,Some(required("--w")?.parse::<usize>().map_err(|e|e.to_string())?))
    };
    validate_params(k,w,mode)?;
    if (experiment==Experiment::C && method==Method::SeqHash)||(experiment!=Experiment::C && method==Method::SimdMinimizers){return Err("method is unavailable for this experiment; see --help".into())}
    let input=fs::canonicalize(required("--input")?).map_err(|e|e.to_string())?;
    let raw=fs::read(&input).map_err(|e|e.to_string())?;
    let dna=parse_input(&raw,if allow_large {(u32::MAX-1) as usize}else{1_000_000})?;
    let root=Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
    let results=fs::canonicalize(root.join("results")).map_err(|e|e.to_string())?;
    let output=PathBuf::from(required("--out")?);
    let parent=fs::canonicalize(output.parent().filter(|p|!p.as_os_str().is_empty()).unwrap_or(Path::new("."))).map_err(|e|format!("output parent must exist: {e}"))?;
    if !parent.starts_with(&results){return Err("output must be a NEW directory below this framework's results/".into())}
    let leaf=output.file_name().ok_or("missing output directory name")?;
    let output=parent.join(leaf);
    if output.exists(){return Err("refusing to overwrite existing output directory".into())}
    let engine=Engine::new(k)?; // table/hasher construction outside every timer
    let mut score_seconds=None;let mut selector_seconds=None;
    let (scores,positions,runtime)=match experiment {
        Experiment::A=>{let s=run_stage(measure,||engine.scores(&dna,method))?;score_seconds=s.seconds;(Some(s.value),None,s.seconds)},
        Experiment::B=>{
            let s=run_stage(measure,||engine.scores(&dna,method))?;
            let p=run_stage(measure,||common_selector(&dna,&s.value,k,w.unwrap(),mode))?;
            score_seconds=s.seconds;selector_seconds=p.seconds;
            (Some(s.value),Some(p.value),s.seconds.zip(p.seconds).map(|(a,b)|a+b))
        },
        Experiment::C=>{let p=run_stage(measure,||engine.end_to_end(&dna,method,w.unwrap(),mode))?;(None,Some(p.value),p.seconds)}
    };
    // Independent postconditions are untimed. Exhaustive window oracles live in smoke.
    if let Some(s)=&scores{validation::check_scores(&engine,&dna,method,s)?;}
    if let Some(p)=&positions{validation::check_positions(&dna,k,w.unwrap(),mode,p,None)?;}
    fs::create_dir(&output).map_err(|e|format!("refusing output creation: {e}"))?;
    let payload=if positions.is_some(){"positions.u32le"}else{"scores.u64le"};
    let f=OpenOptions::new().write(true).create_new(true).open(output.join(payload)).map_err(|e|e.to_string())?;
    let mut writer=BufWriter::new(f);
    if let Some(p)=&positions{for &v in p{writer.write_all(&v.to_le_bytes()).map_err(|e|e.to_string())?;}}
    else if let Some(s)=&scores{for &v in s{writer.write_all(&v.to_le_bytes()).map_err(|e|e.to_string())?;}}
    writer.flush().map_err(|e|e.to_string())?;
    let count=score_count(dna.len(),k);
    let nmin=positions.as_ref().map(|p|p.len());
    let checksum=positions.as_ref().map(|p|checksum_positions(p)).unwrap_or_else(||checksum_u64(scores.as_ref().unwrap()));
    let metadata=json!({
        "schema_version":1,"experiment":experiment.name(),"method":method.name(),
        "input":input,"input_bases":dna.len(),"k":k,"w":w,
        "mode":if experiment==Experiment::A{"canonical-score"}else{mode.name()},
        "canonical_score":true,"kssd_seed":42,"kssd_table_checksum":format!("{:016x}",engine.kssd.table_checksum()),
        "score_count":count,"number_of_minimizers":nmin,
        "density":nmin.map(|n|if count==0{0.0}else{n as f64/count as f64}),
        "timing_enabled":measure,"runtime_seconds":runtime,"score_seconds":score_seconds,"selector_seconds":selector_seconds,
        "throughput_bases_per_second":runtime.filter(|&t|t>0.0).map(|t|dna.len() as f64/t),
        "score_throughput_per_second":score_seconds.filter(|&t|t>0.0).map(|t|count as f64/t),
        "output_file":payload,"output_size_bytes":positions.as_ref().map(|p|p.len()*4).unwrap_or(count*8),
        "output_checksum":format!("{checksum:016x}"),
        "score_storage":if experiment==Experiment::C {None}else{Some("u64; ntHash u32 losslessly widened")}, "position_storage":"little-endian u32; zero-based k-mer start",
        "position_order":"window traversal order; adjacent dedup only",
        "ranking":if method==Method::SimdMinimizers{"native high 16 bits of ntHash32"}else if method==Method::SeqHash{"full ntHash32"}else{"full KSSD 2k-bit score"},
        "upstream":serde_json::from_str::<serde_json::Value>(include_str!("../../third_party/versions.json")).map_err(|e|e.to_string())?
    });
    write_new(&output.join("metadata.json"),&serde_json::to_vec_pretty(&metadata).map_err(|e|e.to_string())?)?;
    println!("OK {} {} -> {}",experiment.name(),method.name(),output.display());
    Ok(())
}
pub fn entry(experiment:Experiment){if let Err(e)=run(experiment){eprintln!("ERROR: {e}");std::process::exit(2);}}
