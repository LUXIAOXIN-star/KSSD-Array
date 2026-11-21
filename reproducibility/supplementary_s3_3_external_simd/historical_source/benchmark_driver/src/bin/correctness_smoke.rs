use kssd_review_simd::{*,validation::*};
use std::fs;

fn verify_case(label:&str,dna:&Dna)->Result<()> {
    let rc=dna.reverse_complement();
    for k in KS {
        let e=Engine::new(k)?;
        if e.kssd.table_checksum()!=Kssd::new(k)?.table_checksum(){return Err("table initialization is nondeterministic".into())}
        for method in [Method::Kssd,Method::SeqHash]{
            let s=e.scores(dna,method)?;let r=e.scores(&rc,method)?;
            check_scores(&e,dna,method,&s)?;check_scores(&e,&rc,method,&r)?;
            if !s.iter().eq(r.iter().rev()){return Err(format!("{label}: canonical score RC mismatch"))}
            if method==Method::SeqHash && dna.len()>=k {
                if s!=e.scalar_nt_scores(dna)||s!=e.published_scores(dna){return Err(format!("{label}: SIMD collector / scalar / published ntHash mismatch"))}
            }
            for (mode,ws) in [(Mode::Strict,STRICT_WS),(Mode::Weak,WEAK_WS)]{
                for w in ws {
                    let b=common_selector(dna,&s,k,w,mode)?;
                    let oracle=reference_positions(dna,&s,k,w,mode,false);
                    check_positions(dna,k,w,mode,&b,Some(&oracle))?;
                    let br=common_selector(&rc,&r,k,w,mode)?;
                    let oracle_rc=reference_positions(&rc,&r,k,w,mode,false);
                    check_positions(&rc,k,w,mode,&br,Some(&oracle_rc))?;
                    let cmethod=if method==Method::Kssd{Method::Kssd}else{Method::SimdMinimizers};
                    let c=e.end_to_end(dna,cmethod,w,mode)?;
                    let coracle=if method==Method::Kssd{oracle}else{reference_positions(dna,&s,k,w,mode,true)};
                    check_positions(dna,k,w,mode,&c,Some(&coracle)).map_err(|err|format!("{label} k={k} w={w} {} {} C: {err}",mode.name(),method.name()))?;
                    let cr=e.end_to_end(&rc,cmethod,w,mode)?;
                    let coracle_rc=if method==Method::Kssd{oracle_rc}else{reference_positions(&rc,&r,k,w,mode,true)};
                    check_positions(&rc,k,w,mode,&cr,Some(&coracle_rc))?;
                    if mode==Mode::Strict && dna.len()>=k {
                        check_rc_positions(dna.len(),k,&b,&br)?;
                        check_rc_positions(dna.len(),k,&c,&cr)?;
                    }
                }
            }
        }
    }
    println!("PASS {label}: scores, selector oracle, native oracle, coordinates, order, adjacent dedup, reverse complement");
    Ok(())
}
fn run()->Result<()> {
    let path=std::env::args().nth(1).ok_or("usage: correctness_smoke SYNTHETIC_1MB.dna")?;
    let raw=fs::read(path).map_err(|e|e.to_string())?;let dna=parse_input(&raw,1_000_000)?;
    if dna.len()!=1_000_000{return Err("primary smoke fixture must be exactly 1,000,000 bases".into())}
    for invalid in [b"ACNT".as_slice(),b">a\nACGT\n>b\nACGT",b"ACGT\n>a\nACGT"]{
        if parse_input(invalid,100).is_ok(){return Err("invalid input was accepted".into())}
    }
    if parse_input(b"ACGT",3).is_ok(){return Err("size guard failed".into())}
    if parse_input(b">x\r\nacgt\r\n",4)?.bytes()!=b"ACGT"{return Err("FASTA normalization failed".into())}
    for k in KS {
        for w in WEAK_WS {if validate_params(k,Some(w),Mode::Strict).is_ok(){return Err("strict parameter guard failed".into())}}
        for w in STRICT_WS {if validate_params(k,Some(w),Mode::Weak).is_ok(){return Err("weak parameter guard failed".into())}}
    }
    verify_case("synthetic_1mb",&dna)?;
    for motif in [b"A".as_slice(),b"C",b"AC",b"ACGT",b"TTTGAAAC",b"GATTACA"] {
        let bytes:Vec<u8>=motif.iter().copied().cycle().take(1025).collect();
        verify_case(&format!("repeat_{}",String::from_utf8_lossy(motif)),&Dna::new(bytes)?)?;
    }
    // Short sequences, exact k/window edges, SIMD lane/padding/transpose boundaries.
    let mut lengths=vec![0,1,18,19,20,21,22,30,31,32,63,64,65,127,128,129,255,256,257,511,512,513,1023];
    for k in KS {for w in STRICT_WS.into_iter().chain(WEAK_WS){lengths.extend([k+w-2,k+w-1,k+w]);}}
    lengths.sort_unstable();lengths.dedup();
    for n in lengths {verify_case(&format!("boundary_{n}"),&Dna::new(dna.bytes()[..n].to_vec())?)?;}
    println!("PASS all correctness checks; no performance timing collected; no cross-method position equality requirement");
    Ok(())
}
fn main(){if let Err(e)=run(){eprintln!("FAIL {e}");std::process::exit(1)}}
