use serde::Deserialize;
use std::fs::File;
use std::io::BufReader;
use std::{cell::RefCell, collections::HashMap, rc::Rc};

type Block = Vec<Exec>;

/// This struct stores immutable data such as code.
#[derive(Debug, Deserialize)]
struct Data {
   functions: Vec<Function>,
}

/// This struct stores mutable state of the program.
#[derive(Debug)]
struct State {
   /// Index to Data.functions
   current_function_id: usize,
   variables: Vec<Value>,
   variables_begin: usize,
}

#[derive(Debug, Deserialize)]
struct Function {
   name: String,
   parameters: Vec<String>,
   variables: Vec<String>,
   body: Block,
}

/// Data-types
#[derive(Debug, Clone)]
enum Value {
   None,
   Bool(bool),
   Int(i64),
   Float(f64),
   Str(Rc<str>),
   Tuple(Rc<Vec<Value>>),
   List(Rc<RefCell<Vec<Value>>>),
   Dict(Rc<RefCell<HashMap<Rc<str>, Value>>>),
}

/// Literal values for primitive data-types
#[derive(Debug, Deserialize)]
enum Literal {
   Nil,
   Bool(bool),
   Int(i64),
   Float(f64),
   Str(String),
}

/// Operators which take 1 parameter
#[derive(Debug, Deserialize)]
enum UnaryOperator {
   Not,
   BitNot,
   Minus,
   Type,
   Bool,
   Int,
   Float,
   Str,
   Len,
   Print,
}

/// Operators which take 2 parameters
#[derive(Debug, Deserialize)]
enum BinaryOperator {
   Add,
   Sub,
   Mul,
   Div,
   Modulo,
   GetItem,
   Eq,
   Is,
   Lt,
   Leq,
   BitAnd,
   BitOr,
   BitXor,
   LeftShift,
   RightShift,
   And,
   Or,
   Push,
   Remove,
   Index,
}

/// Operators which take 3 parameters
#[derive(Debug, Deserialize)]
enum TernaryOperator {
   Branch,
   SetItem,
}

/// Operators which take any no. of parameters
#[derive(Debug, Deserialize)]
enum NaryOperator {
   Tuple,
   List,
}

/// Reference stores index to variables or functions
#[derive(Debug, Deserialize)]
enum Reference {
   /// Index offset to Data.variables
   Variable(usize),
   /// Index to Data.functions
   Function(usize),
}

/// Statements
#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
enum Exec {
   While {
      condition: Expr,
      block: Block,
   },
   DoWhile {
      block: Block,
      condition: Expr,
   },
   Branch {
      condition: Expr,
      then: Block,
      otherwise: Block,
   },
   Return {
      expr: Expr,
   },
   /// Statement comprising of a expression whose evaluated value is immediately dropped.
   Expr {
      expr: Expr,
   },
}

/// Expressions
#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
enum Expr {
   Literal {
      literal: Literal,
   },
   Reference {
      reference: Reference,
   },
   UnaryOperation {
      operator: UnaryOperator,
      expr: Box<Expr>,
   },
   BinaryOperation {
      operator: BinaryOperator,
      left: Box<Expr>,
      right: Box<Expr>,
   },
   TernaryOperation {
      operator: TernaryOperator,
      first: Box<Expr>,
      second: Box<Expr>,
      third: Box<Expr>,
   },
   NaryOperation {
      operator: NaryOperator,
      parameters: Vec<Expr>,
   },
   Call {
      variable: Reference,
      parameters: Vec<Expr>,
   },
   Dict {
      pairs: Vec<(Expr, Expr)>,
   },
   SetVar {
      variable: Reference,
      expr: Box<Expr>,
   },
}

// Cache for the values returned by the type name operator.
thread_local! {
   static TYPE_NAME_NONE: Value = Value::Str("None".into());
   static TYPE_NAME_BOOL: Value = Value::Str("Bool".into());
   static TYPE_NAME_INT: Value = Value::Str("Int".into());
   static TYPE_NAME_FLOAT: Value = Value::Str("Float".into());
   static TYPE_NAME_STR: Value = Value::Str("Str".into());
   static TYPE_NAME_TUPLE: Value = Value::Str("Tuple".into());
   static TYPE_NAME_LIST: Value = Value::Str("List".into());
   static TYPE_NAME_DICT: Value = Value::Str("Dict".into());
}

/// Python-like modulo operator for integers.
fn imod(left: i64, right: i64) -> i64 {
   let mut result = left % right;
   if (result < 0) != (right < 0) {
      result += right;
   }
   result
}

/// Python-like modulo operator for floats.
fn fmod(left: f64, right: f64) -> f64 {
   let mut result = left % right;
   if (result < 0.) != (right < 0.) {
      result += right;
   }
   result
}

impl std::fmt::Display for Value {
   fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
      match self {
         Value::None => {
            write!(f, "none")?;
         },
         Value::Bool(bool) => {
            if *bool {
               write!(f, "true")?;
            } else {
               write!(f, "false")?;
            };
         },
         Value::Int(int) => {
            write!(f, "{int}")?;
         },
         Value::Float(float) => {
            write!(f, "{float}")?;
         },
         Value::Str(str) => {
            write!(f, "{str}")?;
         },
         Value::Tuple(tuple) => {
            write!(f, "{{")?;
            for (i, value) in tuple.iter().enumerate() {
               value.fmt(f)?;
               if i != tuple.len() - 1 {
                  write!(f, ", ")?;
               }
            }
            write!(f, "}}")?;
         },
         Value::List(list) => {
            let list = list.borrow();
            write!(f, "[")?;
            for (i, value) in list.iter().enumerate() {
               value.fmt(f)?;
               if i != list.len() - 1 {
                  write!(f, ", ")?;
               }
            }
            write!(f, "]")?;
         },
         Value::Dict(dict) => {
            let dict = dict.borrow();
            write!(f, "{{ ")?;
            for (i, (k, v)) in dict.iter().enumerate() {
               write!(f, "{k}: ")?;
               v.fmt(f)?;
               if i != dict.len() - 1 {
                  write!(f, ", ")?;
               }
            }
            write!(f, " }}")?;
         },
      };
      Ok(())
   }
}

impl Value {
   /// Must be used to use Value's as conditions.
   fn is_truthy(&self) -> bool {
      match self {
         Value::None => false,
         Value::Bool(bool) => *bool,
         _ => true,
      }
   }

   fn print(self) -> Value {
      println!("{self}");
      Value::None
   }

   fn add(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => Value::Int(left as i64 + right as i64),
         (Value::Bool(left), Value::Int(right)) => Value::Int(left as i64 + right),
         (Value::Bool(left), Value::Float(right)) => Value::Float(f64::from(left) + right),
         (Value::Int(left), Value::Bool(right)) => Value::Int(left + right as i64),
         (Value::Float(left), Value::Bool(right)) => Value::Float(left + f64::from(right)),
         (Value::Int(left), Value::Int(right)) => Value::Int(left + right),
         (Value::Int(left), Value::Float(right)) => Value::Float(left as f64 + right),
         (Value::Float(left), Value::Int(right)) => Value::Float(left + right as f64),
         (Value::Float(left), Value::Float(right)) => Value::Float(left + right),
         (Value::Str(left), Value::Str(right)) => Value::Str(Rc::from(format!("{left}{right}"))),
         (Value::Tuple(left), Value::Tuple(right)) => Value::Tuple(Rc::new(left.iter().chain(right.iter()).cloned().collect())),
         (Value::List(left), Value::List(right)) => Value::List(Rc::new(RefCell::new({
            left.borrow().iter().chain(right.borrow().iter()).cloned().collect()
         }))),
         (Value::Dict(left), Value::Dict(right)) => Value::Dict(Rc::new(RefCell::new(
            left
               .borrow()
               .iter()
               .chain(right.borrow().iter())
               .map(|(k, v)| (k.clone(), v.clone()))
               .collect(),
         ))),
         _ => Value::None,
      }
   }

   fn sub(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => Value::Int(left as i64 - right as i64),
         (Value::Bool(left), Value::Int(right)) => Value::Int(left as i64 - right),
         (Value::Bool(left), Value::Float(right)) => Value::Float(f64::from(left) - right),
         (Value::Int(left), Value::Bool(right)) => Value::Int(left - right as i64),
         (Value::Float(left), Value::Bool(right)) => Value::Float(left - f64::from(right)),
         (Value::Int(left), Value::Int(right)) => Value::Int(left - right),
         (Value::Int(left), Value::Float(right)) => Value::Float(left as f64 - right),
         (Value::Float(left), Value::Int(right)) => Value::Float(left - right as f64),
         (Value::Float(left), Value::Float(right)) => Value::Float(left - right),
         _ => Value::None,
      }
   }

   fn minus(self) -> Value {
      match self {
         Value::Bool(value) => Value::Int(-(value as i64)),
         Value::Int(value) => Value::Int(-value),
         Value::Float(value) => Value::Float(-value),
         _ => Value::None,
      }
   }

   fn mul(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => Value::Int(left as i64 + right as i64),
         (Value::Bool(left), Value::Int(right)) => Value::Int(left as i64 * right),
         (Value::Bool(left), Value::Float(right)) => Value::Float(f64::from(left) * right),
         (Value::Int(left), Value::Bool(right)) => Value::Int(left * right as i64),
         (Value::Float(left), Value::Bool(right)) => Value::Float(left * f64::from(right)),
         (Value::Int(left), Value::Int(right)) => Value::Int(left * right),
         (Value::Int(left), Value::Float(right)) => Value::Float(left as f64 * right),
         (Value::Float(left), Value::Int(right)) => Value::Float(left * right as f64),
         (Value::Float(left), Value::Float(right)) => Value::Float(left * right),
         (Value::Str(str), Value::Int(factor)) => {
            if 0 < factor {
               Value::Str(str.repeat(factor as usize).into())
            } else {
               Value::Str(format!("").into())
            }
         },
         (Value::Tuple(tuple), Value::Int(factor)) => {
            if 0 <= factor {
               Value::Tuple(Rc::new(
                  std::iter::repeat_with(|| tuple.iter())
                     .take(factor as usize)
                     .flatten()
                     .cloned()
                     .collect(),
               ))
            } else {
               Value::None
            }
         },
         (Value::List(list), Value::Int(factor)) => {
            if 0 <= factor {
               let list = list.borrow();
               let list = std::iter::repeat_with(|| list.iter())
                  .take(factor as usize)
                  .flatten()
                  .cloned()
                  .collect();
               Value::List(Rc::new(RefCell::new(list)))
            } else {
               Value::None
            }
         },
         _ => Value::None,
      }
   }

   fn div(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => Value::Int(left as i64 / right as i64),
         (Value::Bool(left), Value::Int(right)) => Value::Int(left as i64 / right),
         (Value::Bool(left), Value::Float(right)) => Value::Float(f64::from(left) / right),
         (Value::Int(left), Value::Bool(right)) => Value::Int(left / right as i64),
         (Value::Float(left), Value::Bool(right)) => Value::Float(left / f64::from(right)),
         (Value::Int(left), Value::Int(right)) => Value::Int(left / right),
         (Value::Int(left), Value::Float(right)) => Value::Float(left as f64 / right),
         (Value::Float(left), Value::Int(right)) => Value::Float(left / right as f64),
         (Value::Float(left), Value::Float(right)) => Value::Float(left / right),
         (Value::Str(_), Value::Str(_)) => unimplemented!(),
         _ => Value::None,
      }
   }

   fn modulo(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => Value::Int(imod(left as i64, right as i64)),
         (Value::Bool(left), Value::Int(right)) => Value::Int(imod(left as i64, right)),
         (Value::Bool(left), Value::Float(right)) => Value::Float(fmod(f64::from(left), right)),
         (Value::Int(left), Value::Bool(right)) => Value::Int(imod(left, right as i64)),
         (Value::Float(left), Value::Bool(right)) => Value::Float(fmod(left, f64::from(right))),
         (Value::Int(left), Value::Int(right)) => Value::Int(imod(left, right)),
         (Value::Int(left), Value::Float(right)) => Value::Float(fmod(left as f64, right)),
         (Value::Float(left), Value::Int(right)) => Value::Float(fmod(left, right as f64)),
         (Value::Float(left), Value::Float(right)) => Value::Float(fmod(left, right)),
         (Value::Str(_), Value::Str(_)) => unimplemented!(),
         _ => Value::None,
      }
   }

   fn eq(&self, other: &Value) -> bool {
      match (self, other) {
         (Value::Bool(left), Value::Bool(right)) => *left == *right,
         (Value::Bool(left), Value::Int(right)) => *left as i64 == *right,
         (Value::Bool(left), Value::Float(right)) => *left as i64 as f64 == *right,
         (Value::Int(left), Value::Bool(right)) => *left == *right as i64,
         (Value::Float(left), Value::Bool(right)) => *left == *right as i64 as f64,
         (Value::Int(left), Value::Int(right)) => *left == *right,
         (Value::Float(left), Value::Float(right)) => *left == *right,
         (Value::Int(left), Value::Float(right)) => *left == *right as i64,
         (Value::Float(left), Value::Int(right)) => *left as i64 == *right,
         (Value::Str(left), Value::Str(right)) => *left == *right,
         (Value::Tuple(left), Value::Tuple(right)) => left.iter().zip(right.iter()).all(|(l, r)| l.eq(r)),
         (Value::List(left), Value::List(right)) => left.borrow().iter().zip(right.borrow().iter()).all(|(l, r)| l.eq(r)),
         _ => false,
      }
   }

   /// Returns true if both Values are the same memory. Will return false for equal but unique values.
   fn is(self, other: Value) -> bool {
      match (self, other) {
         (Value::Str(left), Value::Str(right)) => Rc::ptr_eq(&left, &right),
         (Value::Tuple(left), Value::Tuple(right)) => Rc::ptr_eq(&left, &right),
         (Value::List(left), Value::List(right)) => Rc::ptr_eq(&left, &right),
         _ => false,
      }
   }

   fn lt(self, other: Value) -> Value {
      match self {
         Value::Bool(left) => match other {
            Value::Bool(right) => Value::Bool(left < right),
            Value::Int(right) => Value::Bool((left as i64) < right),
            Value::Float(right) => Value::Bool((left as i64 as f64) < right),
            _ => Value::None,
         },
         Value::Int(left) => match other {
            Value::Bool(right) => Value::Bool(left < right as i64),
            Value::Int(right) => Value::Bool(left < right),
            Value::Float(right) => Value::Bool((left as f64) < right),
            _ => Value::None,
         },
         Value::Float(left) => match other {
            Value::Bool(right) => Value::Bool(left < right as i64 as f64),
            Value::Int(right) => Value::Bool(left < right as f64),
            Value::Float(right) => Value::Bool(left < right),
            _ => Value::None,
         },
         _ => Value::None,
      }
   }

   fn leq(self, other: Value) -> Value {
      match self {
         Value::Bool(left) => match other {
            Value::Bool(right) => Value::Bool(left <= right),
            Value::Int(right) => Value::Bool((left as i64) <= right),
            Value::Float(right) => Value::Bool((left as i64 as f64) <= right),
            _ => Value::None,
         },
         Value::Int(left) => match other {
            Value::Bool(right) => Value::Bool(left <= right as i64),
            Value::Int(right) => Value::Bool(left <= right),
            Value::Float(right) => Value::Bool((left as f64) <= right),
            _ => Value::None,
         },
         Value::Float(left) => match other {
            Value::Bool(right) => Value::Bool(left <= right as i64 as f64),
            Value::Int(right) => Value::Bool(left <= right as f64),
            Value::Float(right) => Value::Bool(left <= right),
            _ => Value::None,
         },
         _ => Value::None,
      }
   }

   fn bitnot(self) -> Value {
      match self {
         Value::Int(int) => Value::Int(!int),
         _ => Value::None,
      }
   }

   fn bitand(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => Value::Int(left & right),
         _ => Value::None,
      }
   }

   fn bitor(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => Value::Int(left | right),
         _ => Value::None,
      }
   }

   fn bitxor(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => Value::Int(left ^ right),
         _ => Value::None,
      }
   }

   fn leftshift(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => Value::Int(left << right),
         _ => Value::None,
      }
   }

   fn rightshift(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => Value::Int(left >> right),
         _ => Value::None,
      }
   }

   fn getitem(self, other: Value) -> Value {
      match (self, other) {
         (Value::Str(str), Value::Int(index)) => (if index < 0 {
            str.chars().nth_back((1 - index) as usize)
         } else {
            str.chars().nth(index as usize)
         })
         .map(|v| Value::Str(Rc::from(format!("{v}"))))
         .unwrap_or(Value::None),
         (Value::Tuple(tuple), Value::Int(mut index)) => {
            if index < 0 {
               index = tuple.len() as i64 - index;
            }
            tuple.get(index as usize).unwrap_or(&Value::None).clone()
         },
         (Value::List(list), Value::Int(mut index)) => {
            let list = list.borrow();
            if index < 0 {
               index = list.len() as i64 - index;
            }
            list.get(index as usize).unwrap_or(&Value::None).clone()
         },
         (Value::Dict(dict), Value::Str(key)) => dict.borrow().get(&*key).unwrap_or(&Value::None).clone(),
         _ => Value::None,
      }
   }

   /// Returns the name of the Value's type as a str.
   fn typename(self) -> Value {
      match self {
         Value::None => TYPE_NAME_NONE.with(|v| v.clone()),
         Value::Bool(_) => TYPE_NAME_BOOL.with(|v| v.clone()),
         Value::Int(_) => TYPE_NAME_INT.with(|v| v.clone()),
         Value::Float(_) => TYPE_NAME_FLOAT.with(|v| v.clone()),
         Value::Str(_) => TYPE_NAME_STR.with(|v| v.clone()),
         Value::Tuple(_) => TYPE_NAME_TUPLE.with(|v| v.clone()),
         Value::List(_) => TYPE_NAME_LIST.with(|v| v.clone()),
         Value::Dict(_) => TYPE_NAME_DICT.with(|v| v.clone()),
      }
   }

   fn not(self) -> Value {
      Value::Bool(!self.is_truthy())
   }

   fn bool(self) -> Value {
      Value::Bool(self.is_truthy())
   }

   fn int(self) -> Value {
      match self {
         Value::Bool(bool) => Value::Int(bool as i64),
         Value::Int(_) => self,
         Value::Float(float) => Value::Int(float as i64),
         Value::Str(_) => unimplemented!(),
         _ => Value::None,
      }
   }

   fn float(self) -> Value {
      match self {
         Value::Bool(bool) => Value::Float(bool as i64 as f64),
         Value::Int(int) => Value::Float(int as f64),
         Value::Float(_) => self,
         Value::Str(_) => unimplemented!(),
         _ => Value::None,
      }
   }

   fn str(self) -> Value {
      Value::Str(format!("{self}").into())
   }

   fn index(self, other: Value) -> Value {
      match self {
         Value::Str(str) => match other {
            Value::Str(substr) => str.find(&*substr).map(|v| Value::Int(v as i64)).unwrap_or(Value::None),
            _ => Value::None,
         },
         Value::Tuple(tuple) => tuple
            .iter()
            .position(|v| v.eq(&other))
            .map(|v| Value::Int(v as i64))
            .unwrap_or(Value::None),
         Value::List(list) => list
            .borrow()
            .iter()
            .position(|v| v.eq(&other))
            .map(|v| Value::Int(v as i64))
            .unwrap_or(Value::None),
         _ => Value::None,
      }
   }

   fn len(self) -> Value {
      match self {
         Value::Str(str) => Value::Int(str.chars().count() as i64),
         Value::Tuple(tuple) => Value::Int(tuple.len() as i64),
         Value::List(list) => Value::Int(list.borrow().len() as i64),
         Value::Dict(dict) => Value::Int(dict.borrow().len() as i64),
         _ => Value::None,
      }
   }

   fn remove(self, other: Value) -> Value {
      match other {
         Value::Int(mut index) => match self {
            Value::List(list) => {
               let mut list = list.borrow_mut();
               if index < 0 {
                  index = list.len() as i64 - index;
               }
               if index < list.len() as i64 {
                  list.remove(index as usize)
               } else {
                  Value::None
               }
            },
            _ => Value::None,
         },
         Value::Str(key) => match self {
            Value::Dict(dict) => dict.borrow_mut().remove(&*key).unwrap_or(Value::None),
            _ => Value::None,
         },
         _ => Value::None,
      }
   }

   fn push(&self, other: Value) -> Value {
      match self {
         Value::List(list) => list.borrow_mut().push(other),
         _ => {},
      }
      Value::None
   }

   fn setitem(&self, key: Value, item: Value) -> Value {
      match self {
         Value::List(list) => match key {
            Value::Int(mut index) => {
               let mut list = list.borrow_mut();
               if index < 0 {
                  index = list.len() as i64 - index;
               }
               if index < list.len() as i64 {
                  list[index as usize] = item;
               }
            },
            _ => {},
         },
         Value::Dict(dict) => match key {
            Value::Str(key) => {
               dict.borrow_mut().insert(key, item);
            },
            _ => {},
         },
         _ => {},
      }
      Value::None
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
         Exec::Branch {
            condition,
            then,
            otherwise,
         } => Exec::branch(data, state, condition, then, otherwise),
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

   fn eval(&self, data: &Data, state: &mut State) -> Value {
      match self {
         Expr::Literal { literal } => match literal {
            // FIXME: Cache literals.
            Literal::Nil => Value::None,
            Literal::Bool(bool) => Value::Bool(*bool),
            Literal::Int(int) => Value::Int(*int),
            Literal::Float(float) => Value::Float(*float),
            Literal::Str(str) => Value::Str(Rc::from(str.clone())),
         },
         Expr::Reference { reference: refer } => match refer {
            Reference::Variable(id) => state.variables[state.variables_begin + *id].clone(),
            Reference::Function(_) => unimplemented!(),
         },
         Expr::UnaryOperation { operator, expr } => match operator {
            UnaryOperator::Not => expr.eval(data, state).not(),
            UnaryOperator::BitNot => expr.eval(data, state).bitnot(),
            UnaryOperator::Minus => expr.eval(data, state).minus(),
            UnaryOperator::Type => expr.eval(data, state).typename(),
            UnaryOperator::Bool => expr.eval(data, state).bool(),
            UnaryOperator::Int => expr.eval(data, state).int(),
            UnaryOperator::Float => expr.eval(data, state).float(),
            UnaryOperator::Str => expr.eval(data, state).str(),
            UnaryOperator::Len => expr.eval(data, state).len(),
            UnaryOperator::Print => expr.eval(data, state).print(),
         },
         Expr::BinaryOperation { operator, left, right } => match operator {
            BinaryOperator::Add => left.eval(data, state).add(right.eval(data, state)),
            BinaryOperator::Sub => left.eval(data, state).sub(right.eval(data, state)),
            BinaryOperator::Mul => left.eval(data, state).mul(right.eval(data, state)),
            BinaryOperator::Div => left.eval(data, state).div(right.eval(data, state)),
            BinaryOperator::Modulo => left.eval(data, state).modulo(right.eval(data, state)),
            BinaryOperator::GetItem => left.eval(data, state).getitem(right.eval(data, state)),
            BinaryOperator::Eq => Value::Bool(left.eval(data, state).eq(&right.eval(data, state))),
            BinaryOperator::Is => Value::Bool(left.eval(data, state).is(right.eval(data, state))),
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
         },
         Expr::TernaryOperation {
            operator,
            first,
            second,
            third,
         } => match operator {
            TernaryOperator::Branch => first.branch(data, state, second, third),
            TernaryOperator::SetItem => first
               .eval(data, state)
               .setitem(second.eval(data, state), third.eval(data, state)),
         },
         Expr::NaryOperation { operator, parameters } => match operator {
            NaryOperator::Tuple => Value::Tuple(Rc::new(parameters.iter().map(|v| v.eval(data, state)).collect())),
            NaryOperator::List => Value::List(Rc::new(RefCell::new(
               parameters.iter().map(|v| v.eval(data, state)).collect(),
            ))),
         },
         Expr::Dict { .. } => unimplemented!(),
         Expr::Call { variable, parameters } => match variable {
            Reference::Function(function_id) => call(data, state, *function_id, parameters).unwrap_or(Value::None),
            Reference::Variable(_) => unimplemented!(),
         },
         Expr::SetVar { variable, expr } => match variable {
            Reference::Variable(id) => {
               let value = expr.eval(data, state);
               state.variables[state.variables_begin + *id] = value.clone();
               value
            },
            Reference::Function(_) => unimplemented!(),
         },
      }
   }
}

fn call(data: &Data, state: &mut State, function_id: usize, parameters: &Vec<Expr>) -> Option<Value> {
   let function = &data.functions[function_id];
   assert!(parameters.len() == function.parameters.len(), "Wrong number of parameters");
   let new_variables_begin = state.variables.len();
   for param in parameters {
      let v = param.eval(data, state);
      state.variables.push(v);
   }
   let old_variables_begin = state.variables_begin;
   state.variables_begin = new_variables_begin;
   for _ in 0..(function.variables.len() - function.parameters.len()) {
      state.variables.push(Value::None);
   }
   let ret = Exec::exec_all(data, state, &function.body);
   state
      .variables
      .truncate(state.variables.len().saturating_sub(function.variables.len()));
   state.variables_begin = old_variables_begin;
   ret
}

fn call_by_name(data: &Data, state: &mut State, function_name: &str, parameters: &Vec<Expr>) -> Option<Value> {
   let mut function = None;
   for (i, func) in data.functions.iter().enumerate() {
      if func.name == function_name {
         function = Some(i);
      }
   }
   if let Some(function) = function {
      call(data, state, function, parameters)
   } else {
      panic!("Function not found: {function_name}")
   }
}

fn main() {
   let file = File::open("project.json").unwrap();
   let reader = BufReader::new(file);
   let data: Data = serde_json::from_reader(reader).unwrap();
   assert!(!data.functions.is_empty());
   let mut state: State = State {
      current_function_id: 0,
      variables: vec![],
      variables_begin: 0,
   };
   call_by_name(&data, &mut state, "main", &vec![]);
}
