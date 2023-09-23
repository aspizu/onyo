use std::cell::RefCell;

use crate::{
   ir::{Data, Expr},
   state::State,
   value::Value
};

pub fn plugin_call(data: &Data, state: &mut State, id: usize, parameters: &Vec<Expr>) -> Value {
   PLUGINS[id](data, state, parameters)
}

static PLUGINS: &[fn(&Data, &mut State, &Vec<Expr>) -> Value] = &[split];

fn split(data: &Data, state: &mut State, parameters: &Vec<Expr>) -> Value {
   if parameters.len() != 2 {
      state.die(data, Value::new_err("Wrong number of arguments to load_json()."), None)
   }
   let Value::Str(string) = parameters[0].eval(data, state) else { return Value::Nil };
   let Value::Str(separator) = parameters[1].eval(data, state) else { return Value::Nil };
   Value::List(RefCell::new(string.split(&*separator).map(|v| v.into()).collect()).into())
}
