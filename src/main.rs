mod fixedarray;
mod ir;
mod misc;
mod state;
mod value;
use std::{env, fs::File, io::BufReader};

use crate::{ir::*, state::*};

fn main() {
   let mut args = env::args();
   args.next().unwrap();
   let file = File::open(args.next().unwrap_or("project.json".to_owned())).unwrap();
   let reader = BufReader::new(file);
   let data: Data = serde_json::from_reader(reader).unwrap();
   let mut state: State = State::new();
   call_by_name(&data, &mut state, "main", &vec![]);
}
