use std::{cell::RefCell, error::Error, fmt::Write, fs, rc::Rc};

use crate::{ir::Data, misc::*};

#[derive(Debug, Clone)]
pub struct Struct {
   pub prototype: usize,
   pub values: Vec<Value>
}

/// Data-types
#[derive(Debug, Clone)]
pub enum Value {
   Nil,
   Err(Box<Value>),
   Bool(bool),
   Int(i64),
   Float(f64),
   Str(Rc<str>),
   List(Rc<RefCell<Vec<Value>>>),
   Struct(Rc<RefCell<Struct>>)
}

impl From<bool> for Value {
   fn from(bool: bool) -> Self {
      Self::Bool(bool)
   }
}

impl From<usize> for Value {
   fn from(int: usize) -> Self {
      Self::Int(int as i64)
   }
}

impl From<i64> for Value {
   fn from(int: i64) -> Self {
      Self::Int(int)
   }
}

impl From<f64> for Value {
   fn from(float: f64) -> Self {
      Self::Float(float)
   }
}

impl From<Struct> for Value {
   fn from(instance: Struct) -> Self {
      Self::Struct(Rc::new(instance.into()))
   }
}

static TYPE_NAME_NIL: &str = "nil";
static TYPE_NAME_ERR: &str = "err";
static TYPE_NAME_BOOL: &str = "bool";
static TYPE_NAME_INT: &str = "int";
static TYPE_NAME_FLOAT: &str = "float";
static TYPE_NAME_STR: &str = "str";
static TYPE_NAME_LIST: &str = "list";
static TYPE_NAME_STRUCT: &str = "struct";

// Cache for the values returned by the type name operator.
thread_local! {
   static TYPE_NAME_NIL_VALUE: Value = Value::Str(TYPE_NAME_NIL.into());
   static TYPE_NAME_ERR_VALUE: Value = Value::Str(TYPE_NAME_ERR.into());
   static TYPE_NAME_BOOL_VALUE: Value = Value::Str(TYPE_NAME_BOOL.into());
   static TYPE_NAME_INT_VALUE: Value = Value::Str(TYPE_NAME_INT.into());
   static TYPE_NAME_FLOAT_VALUE: Value = Value::Str(TYPE_NAME_FLOAT.into());
   static TYPE_NAME_STR_VALUE: Value = Value::Str(TYPE_NAME_STR.into());
   static TYPE_NAME_LIST_VALUE: Value = Value::Str(TYPE_NAME_LIST.into());
   static TYPE_NAME_STRUCT_VALUE: Value = Value::Str(TYPE_NAME_STRUCT.into());
}

impl Struct {
   pub fn eq(&self, other: &Struct) -> bool {
      self.prototype != other.prototype && self.values.iter().zip(other.values.iter()).all(|(left, right)| left.eq(right))
   }
}

impl Value {
   pub fn fmt_join<T, F>(data: &Data, into: &mut String, values: impl Iterator<Item = T>, sep: &str, fmt: F)
   where F: Fn(T, &Data, &mut String) {
      let mut it = values.peekable();
      while let Some(item) = it.next() {
         fmt(item, data, into);
         if it.peek().is_some() {
            write!(into, "{sep}").unwrap();
         }
      }
   }

   pub fn fmt(&self, data: &Data, into: &mut String) {
      match self {
         Value::Nil => write!(into, "{TYPE_NAME_NIL}").unwrap(),
         Value::Bool(true) => write!(into, "true").unwrap(),
         Value::Bool(false) => write!(into, "false").unwrap(),
         Value::Err(err) => err.fmt(data, into),
         Value::Int(int) => write!(into, "{int}").unwrap(),
         Value::Float(float) => write!(into, "{float}").unwrap(),
         Value::Str(str) => write!(into, "\"{str}\"").unwrap(),
         Value::List(list) => {
            write!(into, "[").unwrap();
            Value::fmt_join(data, into, list.borrow().iter(), ", ", |v, data, into| v.fmt(data, into));
            write!(into, "]").unwrap();
         },
         Value::Struct(instance) => {
            let instance = instance.borrow();
            write!(into, "{{").unwrap();
            let prototype = &data.prototypes[instance.prototype];
            Value::fmt_join(data, into, prototype.field_map.iter(), ", ", |(field_id, index), data, into| {
               write!(into, "{}: ", data.ident_map[field_id]).unwrap();
               instance.values[*index].fmt(data, into)
            });
            write!(into, "}}").unwrap();
         }
      }
   }

   /// Must be used to use Value's as conditions.
   pub fn is_truthy(&self) -> bool {
      match self {
         Value::Nil | Value::Err(_) | Value::Bool(false) => false,
         _ => true
      }
   }

   pub fn print(self, data: &Data) -> Value {
      let mut s = String::new();
      self.fmt(data, &mut s);
      println!("{s}");
      Value::Nil
   }

   pub fn add(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => (left as i64 + right as i64).into(),
         (Value::Bool(left), Value::Int(right)) => (left as i64 + right).into(),
         (Value::Bool(left), Value::Float(right)) => (f64::from(left) + right).into(),
         (Value::Int(left), Value::Bool(right)) => (left + right as i64).into(),
         (Value::Float(left), Value::Bool(right)) => (left + f64::from(right)).into(),
         (Value::Int(left), Value::Int(right)) => (left + right).into(),
         (Value::Int(left), Value::Float(right)) => (left as f64 + right).into(),
         (Value::Float(left), Value::Int(right)) => (left + right as f64).into(),
         (Value::Float(left), Value::Float(right)) => (left + right).into(),
         (Value::Str(left), Value::Str(right)) => Value::Str(format!("{left}{right}").into()),
         (Value::List(left), Value::List(right)) =>
            Value::List(RefCell::new(left.borrow().iter().chain(right.borrow().iter()).cloned().collect()).into()),
         _ => Value::Nil
      }
   }

   pub fn sub(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => (left as i64 - right as i64).into(),
         (Value::Bool(left), Value::Int(right)) => (left as i64 - right).into(),
         (Value::Bool(left), Value::Float(right)) => (f64::from(left) - right).into(),
         (Value::Int(left), Value::Bool(right)) => (left - right as i64).into(),
         (Value::Float(left), Value::Bool(right)) => (left - f64::from(right)).into(),
         (Value::Int(left), Value::Int(right)) => (left - right).into(),
         (Value::Int(left), Value::Float(right)) => (left as f64 - right).into(),
         (Value::Float(left), Value::Int(right)) => (left - right as f64).into(),
         (Value::Float(left), Value::Float(right)) => (left - right).into(),
         _ => Value::Nil
      }
   }

   pub fn minus(self) -> Value {
      match self {
         Value::Bool(value) => (-(value as i64)).into(),
         Value::Int(value) => (-value).into(),
         Value::Float(value) => (-value).into(),
         _ => Value::Nil
      }
   }

   pub fn mul(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => (left as i64 * right as i64).into(),
         (Value::Bool(left), Value::Int(right)) => (left as i64 * right).into(),
         (Value::Bool(left), Value::Float(right)) => (f64::from(left) * right).into(),
         (Value::Int(left), Value::Bool(right)) => (left * right as i64).into(),
         (Value::Float(left), Value::Bool(right)) => (left * f64::from(right)).into(),
         (Value::Int(left), Value::Int(right)) => (left * right).into(),
         (Value::Int(left), Value::Float(right)) => (left as f64 * right).into(),
         (Value::Float(left), Value::Int(right)) => (left * right as f64).into(),
         (Value::Float(left), Value::Float(right)) => (left * right).into(),
         (Value::Str(str), Value::Int(factor)) =>
            if 0 <= factor {
               Value::Str(str.repeat(factor as usize).into())
            } else {
               Value::Str("".into())
            },
         (Value::List(list), Value::Int(factor)) =>
            if 0 <= factor {
               let list = list.borrow();
               let list = std::iter::repeat_with(|| list.iter()).take(factor as usize).flatten().cloned().collect();
               Value::List(RefCell::new(list).into())
            } else {
               Value::List(Rc::new(vec![].into()))
            },
         _ => Value::Nil
      }
   }

   pub fn div(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => (left as i64 / right as i64).into(),
         (Value::Bool(left), Value::Int(right)) => (left as i64 / right).into(),
         (Value::Bool(left), Value::Float(right)) => (f64::from(left) / right).into(),
         (Value::Int(left), Value::Bool(right)) => (left / right as i64).into(),
         (Value::Float(left), Value::Bool(right)) => (left / f64::from(right)).into(),
         (Value::Int(left), Value::Int(right)) => (left / right).into(),
         (Value::Int(left), Value::Float(right)) => (left as f64 / right).into(),
         (Value::Float(left), Value::Int(right)) => (left / right as f64).into(),
         (Value::Float(left), Value::Float(right)) => (left / right).into(),
         (Value::Str(_), Value::Str(_)) => unimplemented!(),
         _ => Value::Nil
      }
   }

   pub fn modulo(self, right: Value) -> Value {
      match (self, right) {
         (Value::Bool(left), Value::Bool(right)) => (modulo(left.into(), right.into())).into(),
         (Value::Bool(left), Value::Int(right)) => (modulo(left.into(), right)).into(),
         (Value::Bool(left), Value::Float(right)) => (fmodulo(left.into(), right)).into(),
         (Value::Int(left), Value::Bool(right)) => (modulo(left, right.into())).into(),
         (Value::Float(left), Value::Bool(right)) => (fmodulo(left, right.into())).into(),
         (Value::Int(left), Value::Int(right)) => (modulo(left, right)).into(),
         (Value::Int(left), Value::Float(right)) => (fmodulo(left as f64, right)).into(),
         (Value::Float(left), Value::Int(right)) => (fmodulo(left, right as f64)).into(),
         (Value::Float(left), Value::Float(right)) => (fmodulo(left, right)).into(),
         (Value::Str(_), Value::Str(_)) => unimplemented!(),
         _ => Value::Nil
      }
   }

   pub fn eq(&self, other: &Value) -> bool {
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
         (Value::Err(left), Value::Err(right)) => left.eq(right),
         (Value::List(left), Value::List(right)) => left.borrow().iter().zip(right.borrow().iter()).all(|(l, r)| l.eq(r)),
         (Value::Struct(left), Value::Struct(right)) => left.borrow().eq(&right.borrow()),
         _ => false
      }
   }

   /// Returns true if both Values are the same memory. Will return false
   /// for equal but unique values.
   pub fn is(&self, other: &Value) -> bool {
      match (self, other) {
         (Value::Err(left), Value::Err(right)) => left.is(right),
         (Value::Str(left), Value::Str(right)) => Rc::ptr_eq(left, right),
         (Value::List(left), Value::List(right)) => Rc::ptr_eq(left, right),
         (Value::Struct(left), Value::Struct(right)) => Rc::ptr_eq(left, right),
         _ => false
      }
   }

   pub fn lt(self, other: Value) -> Value {
      match self {
         Value::Bool(left) => match other {
            Value::Bool(right) => (left < right).into(),
            Value::Int(right) => ((left as i64) < right).into(),
            Value::Float(right) => ((left as i64 as f64) < right).into(),
            _ => Value::Nil
         },
         Value::Int(left) => match other {
            Value::Bool(right) => (left < right as i64).into(),
            Value::Int(right) => (left < right).into(),
            Value::Float(right) => ((left as f64) < right).into(),
            _ => Value::Nil
         },
         Value::Float(left) => match other {
            Value::Bool(right) => (left < right as i64 as f64).into(),
            Value::Int(right) => (left < right as f64).into(),
            Value::Float(right) => (left < right).into(),
            _ => Value::Nil
         },
         _ => Value::Nil
      }
   }

   pub fn leq(self, other: Value) -> Value {
      match self {
         Value::Bool(left) => match other {
            Value::Bool(right) => (left <= right).into(),
            Value::Int(right) => ((left as i64) <= right).into(),
            Value::Float(right) => ((left as i64 as f64) <= right).into(),
            _ => Value::Nil
         },
         Value::Int(left) => match other {
            Value::Bool(right) => (left <= right as i64).into(),
            Value::Int(right) => (left <= right).into(),
            Value::Float(right) => ((left as f64) <= right).into(),
            _ => Value::Nil
         },
         Value::Float(left) => match other {
            Value::Bool(right) => (left <= right as i64 as f64).into(),
            Value::Int(right) => (left <= right as f64).into(),
            Value::Float(right) => (left <= right).into(),
            _ => Value::Nil
         },
         _ => Value::Nil
      }
   }

   pub fn bitnot(self) -> Value {
      match self {
         Value::Int(int) => (!int).into(),
         _ => Value::Nil
      }
   }

   pub fn bitand(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => (left & right).into(),
         _ => Value::Nil
      }
   }

   pub fn bitor(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => (left | right).into(),
         _ => Value::Nil
      }
   }

   pub fn bitxor(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => (left ^ right).into(),
         _ => Value::Nil
      }
   }

   pub fn leftshift(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => (left << right).into(),
         _ => Value::Nil
      }
   }

   pub fn rightshift(self, other: Value) -> Value {
      match (self, other) {
         (Value::Int(left), Value::Int(right)) => (left >> right).into(),
         _ => Value::Nil
      }
   }

   pub fn getitem(self, other: Value) -> Value {
      match (self, other) {
         (Value::Str(str), Value::Int(index)) =>
            (if index < 0 { str.chars().nth_back((1 - index) as usize) } else { str.chars().nth(index as usize) })
               .map(|v| Value::Str(Rc::from(v.to_string())))
               .unwrap_or(Value::Nil),
         (Value::List(list), Value::Int(mut index)) => {
            let list = list.borrow();
            if index < 0 {
               index = list.len() as i64 - index;
            }
            list.get(index as usize).unwrap_or(&Value::Nil).clone()
         },
         _ => Value::Nil
      }
   }

   /// Returns the name of the Value's type as a str.
   pub fn typename(self, data: &Data) -> Value {
      match self {
         Value::Nil => TYPE_NAME_NIL_VALUE.with(|v| v.clone()),
         Value::Err(_) => TYPE_NAME_ERR_VALUE.with(|v| v.clone()),
         Value::Bool(_) => TYPE_NAME_BOOL_VALUE.with(|v| v.clone()),
         Value::Int(_) => TYPE_NAME_INT_VALUE.with(|v| v.clone()),
         Value::Float(_) => TYPE_NAME_FLOAT_VALUE.with(|v| v.clone()),
         Value::Str(_) => TYPE_NAME_STR_VALUE.with(|v| v.clone()),
         Value::List(_) => TYPE_NAME_LIST_VALUE.with(|v| v.clone()),
         Value::Struct(instance) => {
            let instance = instance.borrow();
            Value::Str(data.prototypes[instance.prototype].name.clone().into())
         } // TODO: Cache this
      }
   }

   pub fn not(self) -> Value {
      (!self.is_truthy()).into()
   }

   pub fn err(self) -> Value {
      match self {
         Value::Err(val) => *val,
         _ => Value::Err(Box::from(self))
      }
   }

   pub fn bool(self) -> Value {
      self.is_truthy().into()
   }

   pub fn int(self) -> Value {
      match self {
         Value::Bool(bool) => (bool as i64).into(),
         Value::Int(_) => self,
         Value::Float(float) => (float as i64).into(),
         Value::Str(_) => unimplemented!(),
         _ => Value::Nil
      }
   }

   pub fn float(self) -> Value {
      match self {
         Value::Bool(bool) => f64::from(bool).into(),
         Value::Int(int) => (int as f64).into(),
         Value::Float(_) => self,
         Value::Str(_) => unimplemented!(),
         _ => Value::Nil
      }
   }

   pub fn str(self, data: &Data) -> Value {
      let mut s = String::new();
      self.fmt(data, &mut s);
      Value::Str(s.into())
   }

   pub fn index(self, other: Value) -> Value {
      match self {
         Value::Str(str) => match other {
            Value::Str(substr) => str.find(&*substr).map(usize::into).unwrap_or(Value::Nil),
            _ => Value::Nil
         },
         Value::List(list) => list.borrow().iter().position(|v| v.eq(&other)).map(usize::into).unwrap_or(Value::Nil),
         _ => Value::Nil
      }
   }

   pub fn len(self) -> Value {
      match self {
         Value::Str(str) => str.chars().count().into(),
         Value::List(list) => list.borrow().len().into(),
         _ => Value::Nil
      }
   }

   pub fn remove(self, other: Value) -> Value {
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
                  Value::Nil
               }
            },
            _ => Value::Nil
         },
         _ => Value::Nil
      }
   }

   pub fn push(self, other: Value) -> Value {
      match self {
         Value::List(list) => list.borrow_mut().push(other),
         _ => {}
      }
      Value::Nil
   }

   pub fn setitem(self, key: Value, item: Value) -> Value {
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
            _ => {}
         },
         _ => {}
      }
      Value::Nil
   }

   pub fn join(&self, data: &Data, other: Value) -> Value {
      let Value::Str(sep) = other else {
         return Value::Nil;
      };
      match self {
         Value::List(list) => {
            let mut s = String::new();
            Value::fmt_join(data, &mut s, list.borrow().iter(), &sep, Value::fmt);
            Value::Str(s.into())
         },

         _ => Value::Nil
      }
   }

   pub fn from_error(error: impl Error) -> Value {
      Value::Err(Value::Str(error.to_string().into()).into())
   }

   pub fn new_err(string: &str) -> Value {
      Value::Err((Value::Str(string.into())).into())
   }

   pub fn read(self) -> Value {
      match self {
         Value::Str(str) => match fs::read_to_string(&*str) {
            Err(err) => Value::from_error(err),
            Ok(str) => Value::Str(str.into())
         },
         _ => Value::new_err("TypeError")
      }
   }

   pub fn write(self, other: Value) -> Value {
      match self {
         Value::Str(path) => match other {
            Value::Str(str) => match fs::write(&*path, &*str) {
               Err(err) => Value::from_error(err),
               Ok(_) => true.into()
            },
            _ => Value::new_err("TypeError")
         },
         _ => Value::new_err("TypeError")
      }
   }
}
