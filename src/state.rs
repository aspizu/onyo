use std::{cell::RefCell, iter::repeat, rc::Rc};

use crate::{ir::*, value::*};

/// This struct stores mutable state of the program.
#[derive(Debug)]
pub struct State {
   /// Index to Data.functions
   variables: Vec<Value>,
   variables_begin: usize,
}

impl State {
   pub fn new() -> Self {
      Self { variables: vec![], variables_begin: 0 }
   }
}

impl Exec {
   /// Run exec for every statement in block and return if returned.
   fn exec_all(data: &Data, state: &mut State, block: &Block) -> Option<Value> {
      for stmt in block {
         if let Some(ret) = stmt.exec(data, state) {
            return Some(ret);
         }
      }
      None
   }

   fn while_(data: &Data, state: &mut State, condition: &Expr, block: &Block) -> Option<Value> {
      while condition.eval(data, state).is_truthy() {
         if let Some(ret) = Exec::exec_all(data, state, block) {
            return Some(ret);
         }
      }
      None
   }

   fn dowhile(data: &Data, state: &mut State, block: &Block, condition: &Expr) -> Option<Value> {
      loop {
         if let Some(ret) = Exec::exec_all(data, state, block) {
            break Some(ret);
         }
         if !condition.eval(data, state).is_truthy() {
            break None;
         }
      }
   }

   fn branch(data: &Data, state: &mut State, condition: &Expr, then: &Block, otherwise: &Block) -> Option<Value> {
      if condition.eval(data, state).is_truthy() {
         Exec::exec_all(data, state, then)
      } else {
         Exec::exec_all(data, state, otherwise)
      }
   }

   /// Evaluate expression and ignore it's return value and return None.
   fn expr(data: &Data, state: &mut State, expr: &Expr) -> Option<Value> {
      expr.eval(data, state);
      None
   }

   fn exec(&self, data: &Data, state: &mut State) -> Option<Value> {
      match self {
         Exec::While { condition, block } => Exec::while_(data, state, condition, block),
         Exec::DoWhile { block, condition } => Exec::dowhile(data, state, block, condition),
         Exec::Return { expr } => Some(expr.eval(data, state)),
         Exec::Expr { expr } => Exec::expr(data, state, expr),
         Exec::Branch { condition, then, otherwise } => Exec::branch(data, state, condition, then, otherwise),
      }
   }
}

impl Expr {
   fn branch(&self, data: &Data, state: &mut State, then: &Expr, otherwise: &Expr) -> Value {
      if self.eval(data, state).is_truthy() {
         then.eval(data, state)
      } else {
         otherwise.eval(data, state)
      }
   }

   fn and(&self, data: &Data, state: &mut State, other: &Expr) -> Value {
      let cond = self.eval(data, state);
      if cond.is_truthy() {
         other.eval(data, state)
      } else {
         cond
      }
   }

   fn or(&self, data: &Data, state: &mut State, other: &Expr) -> Value {
      let cond = self.eval(data, state);
      if cond.is_truthy() {
         cond
      } else {
         other.eval(data, state)
      }
   }

   fn get_variable(state: &mut State, id: &usize) -> Value {
      state.variables[state.variables_begin + *id].clone()
   }

   fn set_variable(variable: &Reference, expr: &Box<Expr>, data: &Data, state: &mut State) -> Value {
      match variable {
         Reference::Variable(id) => {
            let value = expr.eval(data, state);
            state.variables[state.variables_begin + *id] = value.clone();
            value
         },
         Reference::Function(_) => unimplemented!(),
      }
   }

   fn make_list(parameters: &Vec<Expr>, data: &Data, state: &mut State) -> Value {
      Value::List(Rc::new(RefCell::new(parameters.iter().map(|v| v.eval(data, state)).collect())))
   }

   fn make_struct(prototype: &usize, values: &Vec<Expr>, data: &Data, state: &mut State) -> Value {
      Struct { prototype: *prototype, values: values.iter().map(|v| v.eval(data, state)).collect() }.into()
   }

   fn set_field(value: &Box<Expr>, data: &Data, state: &mut State, instance: &Expr, field_id: &usize) -> Value {
      let value = value.eval(data, state);
      match instance.eval(data, state) {
         Value::Struct(instance) => {
            let mut instance = instance.borrow_mut();
            let prototype = &data.prototypes[instance.prototype];
            instance.values[prototype.field_map[field_id]] = value.clone();
         },
         _ => {},
      }
      value
   }

   fn get_field(instance: &Box<Expr>, data: &Data, state: &mut State, field_id: &usize) -> Value {
      match instance.eval(data, state) {
         Value::Struct(instance_cell) => {
            let instance = instance_cell.borrow();
            let prototype = &data.prototypes[instance.prototype];
            if let Some(&id) = prototype.field_map.get(field_id) {
               instance.values[id].clone()
            } else if let Some(&id) = prototype.method_map.get(field_id) {
               Value::Method { function_id: id, instance: instance_cell.clone() }
            } else {
               Value::new_err("FieldDoesNotExist")
            }
         },
         _ => Value::Nil,
      }
   }

   fn eval(&self, data: &Data, state: &mut State) -> Value {
      match self {
         Expr::Literal { literal } => match literal {
            // FIXME: Cache literals.
            Literal::Nil => Value::Nil,
            Literal::Bool(bool) => Value::Bool(*bool),
            Literal::Int(int) => Value::Int(*int),
            Literal::Float(float) => Value::Float(*float),
            Literal::Str(str) => Value::Str(str.clone().into()),
         },
         Expr::Reference { reference: refer } => match refer {
            Reference::Variable(id) => Expr::get_variable(state, id),
            &Reference::Function(function_id) => Value::Function(function_id),
         },
         Expr::UnaryOperation { operator, expr } => match operator {
            UnaryOperator::Not => expr.eval(data, state).not(),
            UnaryOperator::BitNot => expr.eval(data, state).bitnot(),
            UnaryOperator::Minus => expr.eval(data, state).minus(),
            UnaryOperator::Type => expr.eval(data, state).typename(data),
            UnaryOperator::Err => expr.eval(data, state).err(),
            UnaryOperator::Bool => expr.eval(data, state).bool(),
            UnaryOperator::Int => expr.eval(data, state).int(),
            UnaryOperator::Float => expr.eval(data, state).float(),
            UnaryOperator::Str => expr.eval(data, state).str(data),
            UnaryOperator::Len => expr.eval(data, state).len(),
            UnaryOperator::Print => expr.eval(data, state).print(data),
            UnaryOperator::Read => expr.eval(data, state).read(),
         },
         Expr::BinaryOperation { operator, left, right } => match operator {
            BinaryOperator::Add => left.eval(data, state).add(right.eval(data, state)),
            BinaryOperator::Sub => left.eval(data, state).sub(right.eval(data, state)),
            BinaryOperator::Mul => left.eval(data, state).mul(right.eval(data, state)),
            BinaryOperator::Div => left.eval(data, state).div(right.eval(data, state)),
            BinaryOperator::Modulo => left.eval(data, state).modulo(right.eval(data, state)),
            BinaryOperator::GetItem => left.eval(data, state).getitem(right.eval(data, state)),
            BinaryOperator::Eq => Value::Bool(left.eval(data, state).eq(&right.eval(data, state))),
            BinaryOperator::Is => Value::Bool(left.eval(data, state).is(&right.eval(data, state))),
            BinaryOperator::Lt => left.eval(data, state).lt(right.eval(data, state)),
            BinaryOperator::Leq => left.eval(data, state).leq(right.eval(data, state)),
            BinaryOperator::BitAnd => left.eval(data, state).bitand(right.eval(data, state)),
            BinaryOperator::BitOr => left.eval(data, state).bitor(right.eval(data, state)),
            BinaryOperator::BitXor => left.eval(data, state).bitxor(right.eval(data, state)),
            BinaryOperator::LeftShift => left.eval(data, state).leftshift(right.eval(data, state)),
            BinaryOperator::RightShift => left.eval(data, state).rightshift(right.eval(data, state)),
            BinaryOperator::And => left.and(data, state, right),
            BinaryOperator::Or => left.or(data, state, right),
            BinaryOperator::Push => left.eval(data, state).push(right.eval(data, state)),
            BinaryOperator::Remove => left.eval(data, state).remove(right.eval(data, state)),
            BinaryOperator::Index => left.eval(data, state).index(right.eval(data, state)),
            BinaryOperator::Join => left.eval(data, state).join(data, right.eval(data, state)),
            BinaryOperator::Write => left.eval(data, state).write(right.eval(data, state)),
         },
         Expr::TernaryOperation { operator, first, second, third } => match operator {
            TernaryOperator::Branch => first.branch(data, state, second, third),
            TernaryOperator::SetItem => first.eval(data, state).setitem(second.eval(data, state), third.eval(data, state)),
         },
         Expr::NaryOperation { operator, parameters } => match operator {
            NaryOperator::List => Expr::make_list(parameters, data, state),
         },
         Expr::Call { callable, parameters } => match callable.eval(data, state) {
            Value::Function(function_id) => call(data, state, function_id, parameters, None).unwrap_or(Value::Nil),
            Value::Method { function_id, instance } => {
               call(data, state, function_id, parameters, Some(Value::Struct(instance))).unwrap_or(Value::Nil)
            },
            _ => Value::new_err("NotCallable"),
         },
         Expr::SetVar { variable, expr } => Expr::set_variable(variable, expr, data, state),
         Expr::Struct { prototype, values } => Expr::make_struct(prototype, values, data, state),
         Expr::SetField { instance, field_id, value } => Expr::set_field(value, data, state, instance, field_id),
         Expr::GetField { instance, field_id } => Expr::get_field(instance, data, state, field_id),
      }
   }
}

fn call(data: &Data, state: &mut State, function_id: usize, parameters: &Vec<Expr>, instance: Option<Value>) -> Option<Value> {
   let function = &data.functions[function_id];
   let new_variables_begin = state.variables.len();
   if let Some(instance) = instance {
      state.variables.push(instance);
   }
   for v in parameters {
      let v = v.eval(data, state);
      state.variables.push(v);
   }
   state.variables.extend(repeat(Value::Nil).take(function.variables.len() - function.parameters.len()));
   let old_variables_begin = state.variables_begin;
   state.variables_begin = new_variables_begin;
   let ret = Exec::exec_all(data, state, &function.body);
   state.variables.truncate(state.variables.len().saturating_sub(function.variables.len()));
   state.variables_begin = old_variables_begin;
   ret
}

pub fn call_by_name(data: &Data, state: &mut State, function_name: &str, parameters: &Vec<Expr>) -> Option<Value> {
   data
      .functions
      .iter()
      .enumerate()
      .find(|(_, function)| function.name == function_name)
      .and_then(|(function_id, _)| call(data, state, function_id, parameters, None))
}
