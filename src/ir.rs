use std::collections::BTreeMap;

use serde::Deserialize;

pub type Block = Vec<Exec>;

/// This struct stores immutable data such as code.
#[derive(Debug, Deserialize)]
pub struct Data {
   pub functions: Vec<Function>,
   pub prototypes: Vec<Prototype>,
   /// ident id -> ident name
   pub ident_map: BTreeMap<usize, String>,
   pub reserved_idents: ReservedIdents,
   pub files: Vec<String>
}

#[derive(Debug, Deserialize)]
pub struct Range {
   /// Index for Data.files
   pub file: usize,
   /// 0-indexed line number
   pub line: usize,
   /// 0-indexed column number
   pub col: usize,
   /// length of token
   pub len: usize
}

#[derive(Debug, Deserialize)]
pub struct ReservedIdents {
   pub next: usize,
   pub __call__: usize
}

#[derive(Debug, Deserialize)]
pub struct Prototype {
   pub name: String,
   /// field ident id -> index for Struct.values
   pub field_map: BTreeMap<usize, usize>,
   /// method ident id -> index for Data.functions
   pub method_map: BTreeMap<usize, usize>
}

#[derive(Debug, Deserialize)]
pub struct Function {
   pub name: String,
   pub parameters: Vec<String>,
   pub variables: Vec<String>,
   pub body: Block
}

/// Literal values for primitive data-types
#[derive(Debug, Deserialize)]
pub enum Literal {
   Nil,
   IterEnd,
   Bool(bool),
   Int(i64),
   Float(f64),
   Str(String)
}

/// Operators which take 1 parameter
#[derive(Debug, Deserialize)]
pub enum UnaryOperator {
   Not,
   BitNot,
   Minus,
   Type,
   Err,
   Bool,
   Int,
   Float,
   Str,
   Len,
   Print,
   Read
}

/// Operators which take 2 parameters
#[derive(Debug, Deserialize)]
pub enum BinaryOperator {
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
   Join,
   Write
}

/// Operators which take 3 parameters
#[derive(Debug, Deserialize)]
pub enum TernaryOperator {
   Branch,
   SetItem
}

/// Operators which take any no. of parameters
#[derive(Debug, Deserialize)]
pub enum NaryOperator {
   List
}

/// Reference stores index to variables or functions
#[derive(Debug, Deserialize)]
pub enum Reference {
   /// Index offset to Data.variables
   Variable(usize),
   /// Index to Data.functions
   Function(usize)
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
pub enum Exec {
   While {
      condition: Expr,
      block: Block
   },
   ForLoop {
      variable: Reference,
      iterator: Expr,
      block: Block
   },
   DoWhile {
      block: Block,
      condition: Expr
   },
   Branch {
      condition: Expr,
      then: Block,
      otherwise: Block
   },
   Return {
      expr: Expr
   },
   /// Statement comprising of a expression whose evaluated value is immediately
   /// dropped.
   Expr {
      expr: Expr
   }
}

#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
pub enum Expr {
   Literal { literal: Literal },
   Reference { reference: Reference },
   UnaryOperation { operator: UnaryOperator, expr: Box<Expr> },
   BinaryOperation { operator: BinaryOperator, left: Box<Expr>, right: Box<Expr> },
   TernaryOperation { operator: TernaryOperator, first: Box<Expr>, second: Box<Expr>, third: Box<Expr> },
   NaryOperation { operator: NaryOperator, parameters: Vec<Expr> },
   Call { callable: Box<Expr>, parameters: Vec<Expr> },
   Plugin { id: usize, parameters: Vec<Expr> },
   Struct { prototype: usize, values: Vec<Expr> },
   SetVar { variable: Reference, expr: Box<Expr> },
   SetField { instance: Box<Expr>, field_id: usize, value: Box<Expr> },
   GetField { instance: Box<Expr>, field_id: usize },
   Die { expr: Box<Expr>, range: Range },
   OrDie { expr: Box<Expr>, range: Range }
}
